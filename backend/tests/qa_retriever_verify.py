# -*- coding: utf-8 -*-
"""QA 独立验证：retriever.build_knowledge_base（检索方式改造）逐条行为证明。

隔离 SQLite 库（tempdir，不碰正式 linkoa.db），用构造数据直接调用 retriever 的
build_knowledge_base / 辅助函数，证明本次改造的 6 条行为成立，并顺带验证
ai_service 防幻觉「空知识库短路」红线。

用法（从 backend 目录）：
    ..\.venv\Scripts\python.exe tests\qa_retriever_verify.py
"""
import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta

# backend/ 加入模块路径（脚本可任意 cwd 运行）
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# 必须先于 app.config 导入设置 DB_URL，指向隔离临时库
_TMPDIR = tempfile.mkdtemp(prefix="qa_retriever_")
_DB_PATH = os.path.join(_TMPDIR, "test.db").replace("\\", "/")
os.environ["DB_URL"] = f"sqlite:///{_DB_PATH}"

from app.database import Base, SessionLocal, engine, prepare_sqlite_indexes  # noqa: E402
from app.models import (  # noqa: E402
    AiConfig,
    Customer,
    CustomerCategory,
    Project,
    ProjectContactRel,
    ProjectDesignerRel,
    SysUser,
)
from app.services import ai_service  # noqa: E402
from app.services.llm import retriever  # noqa: E402

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, cond, detail: str = ""):
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
        print(f"  [FAIL] {name}: {detail}")


# ---------------------------------------------------------------------------
# 构造数据
# ---------------------------------------------------------------------------
def setup_data():
    prepare_sqlite_indexes()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    today = date.today()
    this_year = datetime.combine(date(today.year, 5, 1), datetime.min.time())
    last_year = datetime.combine(date(today.year - 1, 6, 1), datetime.min.time())
    expect_soon = datetime.combine(today + timedelta(days=1), datetime.min.time())

    cat_a = CustomerCategory(category_name="单位甲")
    cat_b = CustomerCategory(category_name="单位乙")
    cat_c = CustomerCategory(category_name="空单位丙")
    db.add_all([cat_a, cat_b, cat_c])
    db.flush()

    cust_a1 = Customer(category_id=cat_a.id, customer_name="对接人甲1")
    cust_a2 = Customer(category_id=cat_a.id, customer_name="对接人甲2")
    cust_b1 = Customer(category_id=cat_b.id, customer_name="对接人乙1")
    cust_c1 = Customer(category_id=cat_c.id, customer_name="对接人丙1")
    db.add_all([cust_a1, cust_a2, cust_b1, cust_c1])
    db.flush()

    designer1 = SysUser(username="qa_designer1", password="x", real_name="设计师小王", role="设计师", is_enable=1)
    designer2 = SysUser(username="qa_designer2", password="x", real_name="设计师小李", role="设计师", is_enable=1)
    db.add_all([designer1, designer2])
    db.flush()

    def mk_project(name, cat_id, cust_id, status, create_time, expect_time):
        p = Project(
            project_name=name,
            category_id=cat_id,
            customer_id=cust_id,
            project_desc=None,
            expect_time=expect_time,
            project_status=status,
            create_user_id=1,
            create_time=create_time,
            update_time=create_time,
        )
        db.add(p)
        db.flush()
        return p

    # 甲：多人对接人 + 多人设计师，进行中
    p1 = mk_project("项目甲", cat_a.id, cust_a1.id, "进行中", this_year, expect_soon)
    # 乙：单人对接人，进行中（隔离对照）
    p2 = mk_project("项目乙", cat_b.id, cust_b1.id, "进行中", last_year, None)
    # 甲：已归档，无 rel 对接人（回退首位），无设计师（未分配），无预计时间
    p3 = mk_project("已归档项目甲", cat_a.id, cust_a1.id, "已归档", last_year, None)

    # 对接人（P1 多人，按 rel.id 升序 → 甲1、甲2；P2 单人）
    db.add(ProjectContactRel(project_id=p1.id, customer_id=cust_a1.id))
    db.add(ProjectContactRel(project_id=p1.id, customer_id=cust_a2.id))
    db.add(ProjectContactRel(project_id=p2.id, customer_id=cust_b1.id))
    # 设计师（P1 多人：小王、小李）
    db.add(ProjectDesignerRel(project_id=p1.id, user_id=designer1.id))
    db.add(ProjectDesignerRel(project_id=p1.id, user_id=designer2.id))
    db.commit()

    return {
        "db": db,
        "cat_a": cat_a, "cat_b": cat_b, "cat_c": cat_c,
        "cust_a1": cust_a1, "cust_a2": cust_a2, "cust_b1": cust_b1, "cust_c1": cust_c1,
        "p1": p1, "p2": p2, "p3": p3,
        "today": today, "this_year": this_year, "expect_soon": expect_soon,
    }


def main() -> int:
    d = setup_data()
    db = d["db"]

    emp_user = {"id": 999, "role": "设计师"}
    cust_a_user = {"id": 1001, "role": "客户", "category_id": d["cat_a"].id}
    cust_b_user = {"id": 1002, "role": "客户", "category_id": d["cat_b"].id}
    cust_c_user = {"id": 1003, "role": "客户", "category_id": d["cat_c"].id}
    cust_no_cat_user = {"id": 1004, "role": "客户"}

    try:
        # ============ 1. 员工全量（进行中 + 已归档都出现） ============
        ctx_e, src_e = retriever.build_knowledge_base(db, emp_user)
        check("1.员工全量：进行中项目出现", "项目甲" in ctx_e and "项目乙" in ctx_e, ctx_e[:200])
        check("1.员工全量：已归档项目出现", "已归档项目甲" in ctx_e, ctx_e[:200])
        check("1.员工全量：sources 含全部3条", len(src_e) == 3, str(src_e))
        check("1.员工全量：sources 结构", all("id" in s and "projectName" in s for s in src_e), str(src_e))

        # ============ 2. 客户按 category_id 隔离 ============
        check("2._scope_category_id(客户甲)=单位甲", retriever._scope_category_id(cust_a_user) == d["cat_a"].id)
        check("2._scope_category_id(员工)=None", retriever._scope_category_id(emp_user) is None)
        ctx_a, src_a = retriever.build_knowledge_base(db, cust_a_user)
        check("2.客户甲只见甲(含已归档甲)", "项目甲" in ctx_a and "已归档项目甲" in ctx_a, ctx_a[:200])
        check("2.客户甲不见乙", "项目乙" not in ctx_a, ctx_a[:200])
        check("2.客户甲 sources 2条", len(src_a) == 2, str(src_a))
        ctx_b, _ = retriever.build_knowledge_base(db, cust_b_user)
        check("2.客户乙只见乙", "项目乙" in ctx_b and "项目甲" not in ctx_b, ctx_b[:200])

        # ============ 3. 模板字段正确 ============
        check("3.多人对接人顿号拼接", "对接人：对接人甲1、对接人甲2" in ctx_e, ctx_e[:300])
        check("3.多人设计师顿号拼接", "我方负责人/设计师：设计师小王、设计师小李" in ctx_e, ctx_e[:300])
        check("3.客户单位", "客户单位：单位甲" in ctx_e and "客户单位：单位乙" in ctx_e, ctx_e[:300])
        check("3.立项时间 YYYY-MM-DD", f"立项时间：{d['this_year'].strftime('%Y-%m-%d')}" in ctx_e, ctx_e[:300])
        check("3.预计结束时间 YYYY-MM-DD", f"预计结束时间：{d['expect_soon'].strftime('%Y-%m-%d')}" in ctx_e, ctx_e[:300])
        check("3.已归档→已结项", "项目状态：已结项" in ctx_e, ctx_e[:300])
        check("3.进行中→进行中", "项目状态：进行中" in ctx_e, ctx_e[:300])
        check("3.无rel对接人回退首位", "对接人：对接人乙1" in ctx_e, ctx_e[:300])
        check("3.无设计师→未分配", "我方负责人/设计师：未分配" in ctx_e, ctx_e[:300])
        check("3.预计时间空→未设置", "预计结束时间：未设置" in ctx_e, ctx_e[:300])

        # ============ 4. 模板不含禁用字段 ============
        for word in ("进度", "当前节点", "逾期", "剩余", "交付紧迫"):
            check(f"4.模板不含「{word}」", word not in ctx_e, ctx_e[:300])

        # ============ 5. 空知识库 ============
        ctx_c, src_c = retriever.build_knowledge_base(db, cust_c_user)
        check("5.无项目客户返回空知识库", ctx_c == "" and src_c == [], f"ctx={ctx_c!r} src={src_c}")
        ctx_nc, src_nc = retriever.build_knowledge_base(db, cust_no_cat_user)
        check("5.category_id缺失客户返回空知识库", ctx_nc == "" and src_nc == [], f"ctx={ctx_nc!r}")

        # ============ 6. 客户账号 dict 用 category_id（非旧 customer_id） ============
        # 旧口径带 customer_id 但无 category_id → 应视为缺失 → 空知识库
        ctx_legacy, _ = retriever.build_knowledge_base(
            db, {"id": 1005, "role": "客户", "customer_id": d["cust_a1"].id})
        check("6.仅customer_id(无category_id)视为无数据", ctx_legacy == "", ctx_legacy[:120])

        # ============ 7. 防幻觉：空知识库短路，不调 LLM ============
        db.add(AiConfig(system_prompt="t", model="deepseek-v4-flash", api_key="sk-test-123", base_url="http://127.0.0.1:8899"))
        db.commit()

        class FakeProvider:
            def __init__(self):
                self.calls = []

            def stream_chat(self, messages, temperature=0.7, max_tokens=2048):
                self.calls.append(messages)
                yield "FAKE"

        fake = FakeProvider()
        ai_service.get_provider = lambda config: fake
        events = []
        for chunk in ai_service.chat_stream(cust_c_user, None, "你们公司有哪些项目"):
            chunk = chunk.strip()
            if chunk.startswith("data:"):
                try:
                    import json
                    events.append(json.loads(chunk[5:].strip()))
                except Exception:
                    pass
        delta_text = "".join(e.get("content", "") for e in events if e.get("type") == "delta")
        check("7.空知识库短路：固定话术", "没有查到" in delta_text and "项目列表" in delta_text, delta_text)
        check("7.空知识库短路：不调LLM", len(fake.calls) == 0, f"calls={len(fake.calls)}")

    finally:
        db.close()

    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"QA retriever 独立验证：通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    for name, err in FAILED:
        print(f"  FAIL {name}: {err}")
    # 清理临时库
    try:
        shutil.rmtree(_TMPDIR, ignore_errors=True)
    except Exception:
        pass
    return 0 if not FAILED else 2


if __name__ == "__main__":
    sys.exit(main())
