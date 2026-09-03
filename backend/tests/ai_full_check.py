# -*- coding: utf-8 -*-
r"""AI 助手全链路自检（检索方式改造）：虚拟数据 + mock LLM，不消耗真实 API。

覆盖：
  1. 客户账号数据隔离（知识库构建层 + 身份注入层双保险）
  2. 空知识库短路防幻觉（知识库为空不调 LLM，如实告知）
  3. 内部员工全量可见（进行中 + 已归档）
  4. AI 对话审计留痕（ai_chat / ai_conversation_* 日志）
  5. 速率限制（per-user 滑动窗口，管理员豁免）
  6. 置顶 / 重命名 / 软删除

用法：先启动后端（start.bat / uvicorn），再
  cd backend && ..\.venv\Scripts\python.exe tests\ai_full_check.py
"""
import json
import os
import sys

# 让脚本可在任意 cwd 下运行：把 backend/ 加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from app.database import SessionLocal
from app.models import AiConversation, AiMessage, Customer, SysOperationLog, SysUser
from app.services import ai_service
from app.services.llm import retriever
from app.utils.exceptions import BusinessException

BASE = "http://127.0.0.1:8000"
PREFIX = "AI全检"

PASSED = []
FAILED = []


def check(name: str, cond, detail: str = ""):
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
        print(f"  [FAIL] {name}: {detail}")


class FakeProvider:
    """mock LLM：记录每次调用收到的 messages，并 yield 固定文本（不联网）"""

    def __init__(self):
        self.calls: list[list[dict]] = []

    def stream_chat(self, messages, temperature=0.7, max_tokens=2048):
        self.calls.append(messages)
        yield "【自检回复】"
        yield "虚拟数据链路正常"


def _collect_events(gen):
    events = []
    for chunk in gen:
        chunk = chunk.strip()
        if chunk.startswith("data:"):
            try:
                events.append(json.loads(chunk[5:].strip()))
            except Exception:
                pass
    return events


def _all_system_text(messages) -> str:
    return "\n".join(m.get("content", "") for m in messages if m.get("role") == "system")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=30)
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    if r.json().get("code") != 200:
        print("登录失败，请确认后端已启动（admin/admin123）")
        return 1
    H = {"Authorization": f"Bearer {r.json()['data']['token']}"}

    # ================= 虚拟数据 =================
    dept_id = client.post("/api/sysDept/add", headers=H, json={
        "deptName": f"{PREFIX}部门", "deptType": "internal"}).json()["data"]["deptId"]

    cat_a = client.post("/api/customerCategory/add", headers=H, json={"categoryName": f"{PREFIX}单位甲"}).json()["data"]["id"]
    cat_b = client.post("/api/customerCategory/add", headers=H, json={"categoryName": f"{PREFIX}单位乙"}).json()["data"]["id"]
    cat_c = client.post("/api/customerCategory/add", headers=H, json={"categoryName": f"{PREFIX}单位丙"}).json()["data"]["id"]

    cust_a1 = client.post("/api/customer/add", headers=H, json={"categoryId": cat_a, "customerName": f"{PREFIX}对接人甲1", "contact": "13800000001"}).json()["data"]["id"]
    cust_a2 = client.post("/api/customer/add", headers=H, json={"categoryId": cat_a, "customerName": f"{PREFIX}对接人甲2", "contact": "13800000002"}).json()["data"]["id"]
    cust_b1 = client.post("/api/customer/add", headers=H, json={"categoryId": cat_b, "customerName": f"{PREFIX}对接人乙1", "contact": "13800000003"}).json()["data"]["id"]
    cust_c1 = client.post("/api/customer/add", headers=H, json={"categoryId": cat_c, "customerName": f"{PREFIX}对接人丙1", "contact": "13800000004"}).json()["data"]["id"]

    emp_id = client.post("/api/sysUser/create", headers=H, json={
        "username": f"ai_emp", "password": "123456", "realName": f"{PREFIX}员工", "deptId": dept_id, "role": "普通"}).json()["data"]["userId"]

    acc_a = client.post("/api/sysUser/create", headers=H, json={
        "username": f"ai_cust_a", "password": "123456", "realName": f"{PREFIX}客户甲账号", "categoryId": cat_a}).json()["data"]["userId"]
    acc_b = client.post("/api/sysUser/create", headers=H, json={
        "username": f"ai_cust_b", "password": "123456", "realName": f"{PREFIX}客户乙账号", "categoryId": cat_b}).json()["data"]["userId"]
    # 单位丙：只建账号，不建项目，用于验证"真正无数据"时的空知识库短路
    acc_c = client.post("/api/sysUser/create", headers=H, json={
        "username": f"ai_cust_c", "password": "123456", "realName": f"{PREFIX}客户丙账号", "categoryId": cat_c}).json()["data"]["userId"]

    proj_a = client.post("/api/project/create", headers=H, json={
        "projectName": f"{PREFIX}项目甲", "categoryId": cat_a, "contactCustomerIds": [cust_a1, cust_a2]}).json()["data"]["projectId"]
    proj_b = client.post("/api/project/create", headers=H, json={
        "projectName": f"{PREFIX}项目乙", "categoryId": cat_b, "contactCustomerIds": [cust_b1]}).json()["data"]["projectId"]

    # 客户账号登录应返回归属公司名
    la = client.post("/api/login", json={"username": "ai_cust_a", "password": "123456"}).json()
    lb = client.post("/api/login", json={"username": "ai_cust_b", "password": "123456"}).json()
    check("客户甲登录返回公司名", (la["data"].get("userInfo") or {}).get("companyName") == f"{PREFIX}单位甲",
          str(la["data"].get("userInfo")))
    check("客户乙登录返回公司名", (lb["data"].get("userInfo") or {}).get("companyName") == f"{PREFIX}单位乙")

    cur_a = {"id": acc_a, "role": "客户", "category_id": cat_a}
    cur_b = {"id": acc_b, "role": "客户", "category_id": cat_b}
    cur_c = {"id": acc_c, "role": "客户", "category_id": cat_c}
    cur_emp = {"id": emp_id, "role": "普通"}

    db = SessionLocal()
    try:
        # ================= 1. 知识库构建层隔离 =================
        ctx_a, src_a = retriever.build_knowledge_base(db, cur_a)
        ctx_b, src_b = retriever.build_knowledge_base(db, cur_b)
        ctx_e, src_e = retriever.build_knowledge_base(db, cur_emp)
        check("隔离：客户甲只看到甲项目", f"{PREFIX}项目甲" in ctx_a and f"{PREFIX}项目乙" not in ctx_a, ctx_a[:200])
        check("隔离：客户乙只看到乙项目", f"{PREFIX}项目乙" in ctx_b and f"{PREFIX}项目甲" not in ctx_b, ctx_b[:200])
        check("隔离：内部员工全量可见", f"{PREFIX}项目甲" in ctx_e and f"{PREFIX}项目乙" in ctx_e, ctx_e[:200])

        # ================= 2. mock LLM 编排 =================
        fake = FakeProvider()
        ai_service.get_provider = lambda config: fake

        # 2a. 空知识库短路：真正无数据（单位丙无任何项目）→ 不调 LLM，如实告知
        ev = _collect_events(ai_service.chat_stream(cur_c, None, "青岛地铁有哪些项目在进行"))
        short_text = "".join(e.get("content", "") for e in ev if e.get("type") == "delta")
        check("防幻觉：查不到如实告知", "没有查到" in short_text, short_text)
        check("防幻觉：短路不调 LLM", len(fake.calls) == 0)

        # 2b. 客户甲问本公司项目 → 调 LLM，身份注入甲、不泄露乙
        fake2 = FakeProvider()
        ai_service.get_provider = lambda config: fake2
        ev2 = _collect_events(ai_service.chat_stream(cur_a, None, f"我们公司有哪些项目在进行"))
        done = next((e for e in ev2 if e.get("type") == "done"), None)
        check("客户甲：流式 done 事件", done is not None and done.get("conversationId") and done.get("messageId"))
        sys_text = _all_system_text(fake2.calls[0])
        check("客户甲：身份注入单位甲", f"{PREFIX}单位甲" in sys_text)
        check("客户甲：不泄露单位乙", f"{PREFIX}单位乙" not in sys_text, sys_text[:300])
        check("客户甲：来源含项目甲", any(s.get("projectName") == f"{PREFIX}项目甲" for s in (done or {}).get("sources", [])))

        # 2c. 内部员工 → 全量上下文
        fake3 = FakeProvider()
        ai_service.get_provider = lambda config: fake3
        ev3 = _collect_events(ai_service.chat_stream(cur_emp, None, "我们公司有哪些项目在进行"))
        sys3 = _all_system_text(fake3.calls[0])
        check("内部员工：上下文含甲乙项目", f"{PREFIX}项目甲" in sys3 and f"{PREFIX}项目乙" in sys3, sys3[:300])

        # ================= 4. 审计留痕 =================
        ai_logs = db.query(SysOperationLog).filter(SysOperationLog.oper_type.like("ai_%")).all()
        check("审计：存在 ai_chat 日志", any(l.oper_type == "ai_chat" for l in ai_logs))

        # ================= 5. 速率限制（in-process 逻辑验证） =================
        ai_service._rate_buckets.clear()
        blocked = False
        try:
            for _ in range(21):
                ai_service._check_rate_limit(999999, "普通")
        except BusinessException as exc:
            blocked = exc.code == 429
        check("限流：普通用户超限 429", blocked)
        ai_service._rate_buckets.clear()
        adm_ok = True
        try:
            for _ in range(30):
                ai_service._check_rate_limit(1, "管理员")
        except BusinessException:
            adm_ok = False
        check("限流：管理员豁免", adm_ok)
        ai_service._rate_buckets.clear()

        # ================= 6. 置顶/重命名/软删（service 层） =================
        cid = ai_service.create_conversation(db, acc_a)
        ai_service.rename_conversation(db, acc_a, cid, "甲置顶会话")
        ai_service.set_conversation_pin(db, acc_a, cid, True)
        lst = ai_service.list_conversations(db, acc_a)
        check("置顶：排在最前", lst and lst[0].id == cid and lst[0].pinned is True)
        ai_service.delete_conversation(db, acc_a, cid)
        lst2 = ai_service.list_conversations(db, acc_a)
        check("软删：列表不再出现", all(c.id != cid for c in lst2))
        still = db.get(AiConversation, cid)
        check("软删：数据仍在库（可溯源）", still is not None and still.is_deleted is True)
        try:
            ai_service.get_messages(db, acc_a, cid)
            check("软删：消息访问被阻断", False)
        except BusinessException:
            check("软删：消息访问被阻断", True)

    finally:
        db.close()

    # ================= 清理 =================
    for pid in (proj_a, proj_b):
        client.post("/api/project/delete", headers=H, json={"projectId": pid})
    for uid in (acc_a, acc_b, acc_c, emp_id):
        client.post("/api/sysUser/delete", headers=H, json={"userId": uid})
    for cid_ in (cust_a1, cust_a2, cust_b1, cust_c1):
        client.post("/api/customer/delete", headers=H, json={"id": cid_})
    for cat in (cat_a, cat_b, cat_c):
        client.post("/api/customerCategory/delete", headers=H, json={"id": cat})
    client.post("/api/sysDept/delete", headers=H, json={"id": dept_id})

    # 物理清理 AI 会话/消息/审计日志（chat_stream 会落库且软删不清除，避免污染正式库）
    _db = SessionLocal()
    try:
        for _uid in (acc_a, acc_b, acc_c, emp_id):
            for _c in _db.query(AiConversation).filter(AiConversation.user_id == _uid).all():
                _db.query(AiMessage).filter(AiMessage.conversation_id == _c.id).delete()
                _db.delete(_c)
        _db.query(SysOperationLog).filter(
            SysOperationLog.oper_user_id.in_([acc_a, acc_b, acc_c, emp_id]),
            SysOperationLog.oper_type.like("ai_%"),
        ).delete(synchronize_session=False)
        _db.commit()
    finally:
        _db.close()

    print("\n" + "=" * 60)
    print(f"AI 全链路自检：通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    for name, err in FAILED:
        print(f"  FAIL {name}: {err}")
    return 0 if not FAILED else 2


if __name__ == "__main__":
    sys.exit(main())
