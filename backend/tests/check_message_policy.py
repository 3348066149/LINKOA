# -*- coding: utf-8 -*-
"""V1.4.21 消息降噪策略自检（TestClient + 临时库副本）

覆盖点：
  1. 常规操作（节点新增/修改/删除、表单填写）**不再生成消息**
  2. 关键事件（客户审核提交、客户评价、新评论）照旧生成
  3. 未读数只统计关键通知（与铃铛红点、消息中心默认展示口径一致）
  4. myList 默认只返回关键通知；includeRoutine=true 才带出常规历史
  5. readAll 支持按项目标记，且默认不误伤隐藏的常规消息

安全约束（重要）：本脚本先把真实库复制到临时目录，并在开始断言前**校验
app.config.settings.DB_URL 确实指向临时副本**，一旦不匹配立即退出，
避免误写生产数据（V1.4.21 曾因为一个相对路径的临时脚本静默回落真实库而误标未读）。

运行：.venv/Scripts/python backend/tests/check_message_policy.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
SRC_DB = os.path.join(PROJECT_ROOT, "data", "linkoa.db")

TMP_DIR = tempfile.mkdtemp(prefix="linkoa_msg_check_")
TMP_DB = os.path.join(TMP_DIR, "linkoa_check.db")
if os.path.isfile(SRC_DB):
    shutil.copy(SRC_DB, TMP_DB)

# 绝对路径写入环境变量（在 import app 之前）
os.environ["DB_URL"] = "sqlite:///" + TMP_DB.replace("\\", "/")
os.environ["UPLOAD_DIR"] = os.path.join(TMP_DIR, "uploads")
os.environ["JWT_SECRET"] = "linkoa-message-check-secret-0123456789"

sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

ok_count = 0
TOTAL = 13
PREFIX = "消息策略自检"
ROUTINE = ("node_create", "node_update", "node_delete", "form_update")


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  [{ok_count}/{TOTAL}] OK  {name}")


def api(client, path, body, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(path, json=body, headers=h).json()


def get(client, path, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get(path, headers=h).json()


def count_msg(db_path, sql, args=()):
    c = sqlite3.connect(db_path)
    try:
        return c.execute(sql, args).fetchone()[0]
    finally:
        c.close()


def main():
    # ---- 0. 隔离护栏：确认真的在用临时副本 ----
    actual = settings.DB_URL.replace("\\", "/").lower()
    assert TMP_DB.replace("\\", "/").lower() in actual, (
        f"隔离校验失败！当前 DB_URL={settings.DB_URL}，不是临时副本 {TMP_DB}；已中止以免误写生产库"
    )
    print(f"隔离校验通过：{settings.DB_URL}")

    client = TestClient(app)
    with client:
        # 副本库自带历史消息，会干扰计数：直接清空 message 表（只作用于临时副本），
        # 让所有断言都有确定的基线
        c = sqlite3.connect(TMP_DB)
        c.execute("delete from message")
        c.commit()
        c.close()

        res = api(client, "/api/login", {"username": "admin", "password": "admin123"})
        assert res["code"] == 200, f"管理员登录失败: {res}"
        at = res["data"]["token"]

        # ---- 造数：客户单位 / 对接人 / 客户账号 / 项目 / 审核节点 ----
        cat_id = api(client, "/api/customerCategory/add", {"categoryName": PREFIX + "单位"}, at)["data"]["id"]
        cid = api(client, "/api/customer/add",
                  {"categoryId": cat_id, "customerName": PREFIX + "对接人", "contact": "000"}, at)["data"]["id"]
        assert api(client, "/api/sysUser/create",
                   {"username": PREFIX + "账号", "password": "check123456",
                    "realName": PREFIX + "客户", "categoryId": cat_id}, at)["code"] == 200
        pid = api(client, "/api/project/create",
                  {"projectName": PREFIX + "项目", "categoryId": cat_id,
                   "contactCustomerIds": [cid]}, at)["data"]["projectId"]

        # 直接补一条设计师关联（用副本库里已有的 id=2 员工），
        # 这样「操作人=创建人 admin」时仍有其它接收人，才能验证常规操作确实没推送
        c = sqlite3.connect(TMP_DB)
        c.execute("insert into project_designer_rel (project_id, user_id, create_time) "
                  "values (?, 2, '2026-10-14 12:00:00')", (pid,))
        c.commit()
        c.close()

        tpl_review = api(client, "/api/nodeTemplate/add", {
            "nodeTitle": PREFIX + "审核节点", "sort": 99, "isReview": True,
            "reviewOptions": ["通过"], "formFields": []}, at)["data"]["id"]
        tpl_normal = api(client, "/api/nodeTemplate/add", {
            "nodeTitle": PREFIX + "普通节点", "sort": 98, "formFields": []}, at)["data"]["id"]

        # ---- 1. 常规操作：新增节点不产生消息 ----
        base_routine = count_msg(TMP_DB, "select count(*) from message where msg_type in (?,?,?,?)", ROUTINE)
        nid = api(client, "/api/projectNode/add", {"projectId": pid, "nodeTemplateId": tpl_normal}, at)["data"]["id"]
        n_routine = count_msg(TMP_DB, "select count(*) from message where msg_type in (?,?,?,?)", ROUTINE)
        check("常规操作（新增节点）不生成任何消息", n_routine == base_routine, f"新增 {n_routine - base_routine} 条")

        api(client, "/api/projectNode/update",
            {"id": nid, "nodeTitle": PREFIX + "改名节点", "sort": 0, "posX": 0, "posY": 0}, at)
        api(client, "/api/projectNode/delete", {"nodeId": nid}, at)
        n_routine = count_msg(TMP_DB, "select count(*) from message where msg_type in (?,?,?,?)", ROUTINE)
        check("常规操作（改节点/删节点）不生成任何消息", n_routine == base_routine, f"新增 {n_routine - base_routine} 条")

        # ---- 2. 关键事件：客户提交审核 → 创建人 + 设计师各收到 1 条 ----
        rnid = api(client, "/api/projectNode/add", {"projectId": pid, "nodeTemplateId": tpl_review}, at)["data"]["id"]
        ct = api(client, "/api/login", {"username": PREFIX + "账号", "password": "check123456"})["data"]["token"]
        res = api(client, "/api/review/submit",
                  {"projectNodeId": rnid, "option": "通过", "comment": "自检", "feedbackFields": []}, ct)
        check("客户审核提交成功", res["code"] == 200, res)
        n_review = count_msg(TMP_DB, "select count(*) from message where msg_type='customer_review'")
        check("关键事件（客户审核）生成消息给创建人+设计师", n_review == 2, f"实际 {n_review} 条")

        # ---- 3. 未读数只算关键通知 ----
        # 人为塞 3 条已存在的常规未读消息（模拟历史噪音）
        c = sqlite3.connect(TMP_DB)
        for i, t in enumerate(("form_update", "node_create", "node_delete")):
            c.execute("insert into message (receive_user_id, project_id, msg_type, msg_content, is_read, create_time) "
                      "values (1, ?, ?, '历史常规消息', 0, '2026-10-14 12:0%d:00')" % i, (pid, t))
        c.commit()
        c.close()
        unread = get(client, "/api/message/unreadCount", at)["data"]["count"]
        check("未读数只统计关键通知（忽略 3 条常规未读）", unread == 1, f"实际 {unread}")

        # ---- 4. myList 默认过滤 / includeRoutine 开关 ----
        default_list = get(client, "/api/message/myList?pageNum=1&pageSize=50", at)["data"]
        check("myList 默认只返回关键通知", default_list["total"] == 1
              and {m["msgType"] for m in default_list["items"]} == {"customer_review"}, default_list["total"])
        routine_list = get(client, "/api/message/myList?pageNum=1&pageSize=50&includeRoutine=true", at)["data"]
        check("includeRoutine=true 带出常规历史", routine_list["total"] == 4, routine_list["total"])

        # ---- 5. readAll：按项目 + 不误伤隐藏的常规消息 ----
        marked = api(client, "/api/message/readAll", {"projectId": pid}, at)["data"]["count"]
        check("按项目全部已读：只标记可见的关键通知", marked == 1, f"实际 {marked}")
        still = count_msg(TMP_DB,
                          "select count(*) from message where receive_user_id=1 and is_read=0 and msg_type in (?,?,?,?)",
                          ROUTINE)
        check("隐藏的常规消息未被误标已读", still == 3, f"实际剩 {still} 条未读")

        marked2 = api(client, "/api/message/readAll",
                      {"projectId": pid, "includeRoutine": True}, at)["data"]["count"]
        check("includeRoutine=true 时连常规一起标记", marked2 == 3, f"实际 {marked2}")
        left = count_msg(TMP_DB, "select count(*) from message where receive_user_id=1 and is_read=0")
        check("该项目下未读已清零", left == 0, f"实际剩 {left}")

        # ---- 6. 评论（白名单内）照旧生成：admin 评论 → 接收人=设计师 id=2 ----
        res = api(client, "/api/comment/add", {"projectId": pid, "content": "自检评论"}, at)
        check("发布评论成功", res["code"] == 200, res)
        n_comment = count_msg(TMP_DB,
                              "select count(*) from message where msg_type='comment_create' and receive_user_id=2")
        check("关键事件（新评论）生成消息给设计师", n_comment == 1, f"实际 {n_comment} 条")

    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    return 0 if ok_count == TOTAL else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        print(f"临时数据已清理：{TMP_DIR}")
    sys.exit(code)
