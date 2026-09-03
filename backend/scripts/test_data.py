"""测试数据生成脚本（幂等：每次运行先清空旧的测试数据，再重建一套全新测试数据）。

用法（由项目根目录的 add_test_data.bat 调用，也可手动执行）：
    .venv/Scripts/python.exe backend/scripts/test_data.py

设计要点：
  1. 所有测试数据带统一标记，便于精准识别、只删测试数据、不碰真实数据：
     - 客户单位 / 对接人 / 项目 / 员工真实姓名：名称以「【测试】」开头
     - 登录账号：username 以「test_」开头
  2. 幂等：再次运行 = 恢复初始状态（先删旧测试数据，再重建），不会重复堆叠。
  3. 不造附件 / 不预置 AI 会话 / 不写操作日志（这些由真实使用产生，不属测试数据）。
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# 让 `app` 包可导入（backend/ 目录），无论从哪个工作目录启动都能正确定位
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# 控制台统一 UTF-8，避免中文乱码（配合 bat 里的 chcp 65001）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from sqlalchemy import delete, select  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import (  # noqa: E402
    Base,
    SessionLocal,
    auto_add_missing_columns,
    engine,
    prepare_sqlite_indexes,
)
from app import models  # noqa: F401,E402  触发全部模型注册到 Base.metadata
from app.models import (  # noqa: E402
    Attachment,
    Comment,
    Customer,
    CustomerCategory,
    Message,
    Project,
    ProjectContactRel,
    ProjectDesignerRel,
    ProjectNode,
    ProjectNodeEdge,
    ProjectNodeFormValue,
    SysDept,
    SysUser,
)

# ---------------------------------------------------------------------------
# 标记常量（clean 与 seed 共用，改这里即可整体替换）
# ---------------------------------------------------------------------------
MARK = "【测试】"          # 名称标记：客户单位 / 对接人 / 项目 / 员工真实姓名
USER_PREFIX = "test_"      # 登录账号标记
PASSWORD = "123456"        # 全部测试账号统一密码

# ---------------------------------------------------------------------------
# 测试数据定义（确定性：每次运行生成完全一致的一套数据）
# ---------------------------------------------------------------------------
# 客户单位：围绕青岛本地的真实风格单位（博物馆/企业/会展/出版/文旅等）
COMPANIES = [
    "青岛市博物馆",
    "青岛啤酒文化传播有限公司",
    "青岛海昌极地海洋公园",
    "青岛国际会展中心",
    "青岛出版集团",
    "青岛崂山风景区管理服务中心",
]
SHORT = ["市博", "青啤", "海昌", "会展", "出版", "崂山"]

CONTACT_NAMES = [
    "王芳", "李强", "赵敏", "陈晨", "刘洋", "孙悦",
    "周婷", "吴磊", "郑爽", "钱进", "冯雪", "沈飞",
    "韩梅", "杨帆", "朱琳", "秦朗", "许倩", "何东",
]

# 内部员工账号：(username, 真实姓名, 部门, 角色)  —— 当前角色仅 普通 / 管理员
STAFF = [
    ("test_admin",     "吴磊", "研发部", "管理员"),
    ("test_designer1", "陈晨", "设计部", "普通"),
    ("test_designer2", "刘洋", "设计部", "普通"),
    ("test_designer3", "孙悦", "设计部", "普通"),
    ("test_staff1",    "周婷", "市场部", "普通"),
]

# 30 个项目名称（按公司顺序分配，每公司 5 个，贴合各单位业务方向）
PROJECT_NAMES = [
    # 青岛市博物馆
    "馆藏文物IP形象设计", "博物馆文创产品开发", "特展主视觉设计", "导览手册设计", "馆庆纪念品包装设计",
    # 青岛啤酒文化传播有限公司
    "啤酒节主视觉设计", "品牌IP形象升级", "联名礼盒包装设计", "啤酒文化展馆视觉设计", "社媒海报系列设计",
    # 青岛海昌极地海洋公园
    "海洋动物吉祥物设计", "主题IP盲盒开发", "园区导视系统设计", "海洋科普绘本设计", "周年庆视觉设计",
    # 青岛国际会展中心
    "国际啤酒节物料设计", "展会空间搭建视觉", "展会主KV设计", "展馆标识系统设计", "招商手册设计",
    # 青岛出版集团
    "图书封面系列设计", "儿童绘本插画设计", "文创书签套装设计", "城市IP形象设计", "年度宣传画册设计",
    # 青岛崂山风景区管理服务中心
    "崂山茶礼盒包装设计", "景区IP形象设计", "崂山文创伴手礼开发", "景区导览图设计", "文旅宣传海报设计",
]

# 三套流程节点序列（与系统预置模板一致；字段三元组 = (标签, 类型, 下拉选项或 None)）
NODE_FLOWS = {
    "ip": [
        ("立项登记", [("立项编号", "text_single", None), ("项目背景", "text_multi", None)]),
        ("需求对齐", [("需求描述", "text_multi", None), ("优先级", "select", ["高", "中", "低"])]),
        ("IP设计输出", [("设计说明", "text_multi", None), ("设计稿版本", "text_single", None)]),
        ("方案内部评审", [("评审结论", "select", ["通过", "修改后通过", "不通过"]), ("评审意见", "text_multi", None)]),
        ("打样制作", [("打样数量", "text_single", None), ("打样备注", "text_multi", None)]),
        ("实物生产", [("生产数量", "text_single", None), ("供应商", "text_single", None)]),
        ("验收", [("验收结论", "select", ["合格", "不合格"]), ("验收备注", "text_multi", None)]),
        ("项目归档", [("归档备注", "text_multi", None)]),
    ],
    "design": [
        ("立项登记", [("立项编号", "text_single", None), ("项目背景", "text_multi", None)]),
        ("需求对齐", [("需求描述", "text_multi", None), ("优先级", "select", ["高", "中", "低"])]),
        ("IP设计输出", [("设计说明", "text_multi", None), ("设计稿版本", "text_single", None)]),
        ("方案内部评审", [("评审结论", "select", ["通过", "修改后通过", "不通过"]), ("评审意见", "text_multi", None)]),
        ("验收", [("验收结论", "select", ["合格", "不合格"]), ("验收备注", "text_multi", None)]),
        ("项目归档", [("归档备注", "text_multi", None)]),
    ],
    "expo": [
        ("立项登记", [("立项编号", "text_single", None), ("项目背景", "text_multi", None)]),
        ("需求对齐", [("需求描述", "text_multi", None), ("优先级", "select", ["高", "中", "低"])]),
        ("IP设计输出", [("设计说明", "text_multi", None), ("设计稿版本", "text_single", None)]),
        ("方案内部评审", [("评审结论", "select", ["通过", "修改后通过", "不通过"]), ("评审意见", "text_multi", None)]),
        ("打样制作", [("打样数量", "text_single", None), ("打样备注", "text_multi", None)]),
        ("布展搭建", [("布展进度", "select", ["未开始", "进行中", "已完成"]), ("现场负责人", "text_single", None), ("布展备注", "text_multi", None)]),
        ("验收", [("验收结论", "select", ["合格", "不合格"]), ("验收备注", "text_multi", None)]),
        ("项目归档", [("归档备注", "text_multi", None)]),
    ],
}
FLOW_ORDER = ["ip", "design", "expo"]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _ensure_schema() -> None:
    """建表 + 补列（与后端启动逻辑同源，保证全新库也能跑）"""
    if settings.DB_URL.startswith("sqlite"):
        prepare_sqlite_indexes()
    Base.metadata.create_all(bind=engine)
    auto_add_missing_columns()


def _ensure_baseline(db) -> int:
    """确保 admin / 内置部门 / 节点模板 / 流程模板存在（幂等），返回 admin 的 id"""
    from app.services import dept_service, template_service

    dept_service.init_default_depts(db)
    template_service.init_default_node_templates(db)
    template_service.init_default_flow_templates(db)

    admin = db.execute(select(SysUser).where(SysUser.username == "admin")).scalars().first()
    if admin is None:
        admin = SysUser(username="admin", password="admin123", real_name="管理员", role="管理员", is_enable=1)
        db.add(admin)
        db.commit()
    return admin.id


def _dept_id_map(db) -> dict:
    return {name: did for did, name in db.execute(select(SysDept.id, SysDept.dept_name)).all()}


def _clean_test_data(db) -> dict:
    """删除所有带标记的测试数据（子表→父表），返回各表删除行数。只动测试数据。"""
    counts = {}

    pids = list(db.execute(select(Project.id).where(Project.project_name.like(f"{MARK}%"))).scalars().all())
    uids = list(db.execute(select(SysUser.id).where(SysUser.username.like(f"{USER_PREFIX}%"))).scalars().all())

    if pids:
        nids = list(db.execute(select(ProjectNode.id).where(ProjectNode.project_id.in_(pids))).scalars().all())
        if nids:
            counts["节点表单值"] = db.execute(
                delete(ProjectNodeFormValue).where(ProjectNodeFormValue.project_node_id.in_(nids))
            ).rowcount
        counts["节点连线"] = db.execute(delete(ProjectNodeEdge).where(ProjectNodeEdge.project_id.in_(pids))).rowcount
        counts["项目节点"] = db.execute(delete(ProjectNode).where(ProjectNode.project_id.in_(pids))).rowcount
        counts["对接人关联"] = db.execute(delete(ProjectContactRel).where(ProjectContactRel.project_id.in_(pids))).rowcount
        counts["设计师关联"] = db.execute(delete(ProjectDesignerRel).where(ProjectDesignerRel.project_id.in_(pids))).rowcount
        counts["附件"] = db.execute(delete(Attachment).where(Attachment.project_id.in_(pids))).rowcount
        counts["评论"] = db.execute(delete(Comment).where(Comment.project_id.in_(pids))).rowcount
        counts["消息"] = db.execute(delete(Message).where(Message.project_id.in_(pids))).rowcount
        counts["项目"] = db.execute(delete(Project).where(Project.id.in_(pids))).rowcount

    if uids:
        counts["测试账号消息"] = db.execute(delete(Message).where(Message.receive_user_id.in_(uids))).rowcount

    counts["对接人"] = db.execute(delete(Customer).where(Customer.customer_name.like(f"{MARK}%"))).rowcount
    counts["客户单位"] = db.execute(delete(CustomerCategory).where(CustomerCategory.category_name.like(f"{MARK}%"))).rowcount
    counts["测试账号"] = db.execute(delete(SysUser).where(SysUser.username.like(f"{USER_PREFIX}%"))).rowcount

    return counts


def _expect_time(i: int, archived: bool) -> datetime:
    r = random.Random(10000 + i)
    now = datetime.now()
    if archived:
        return now - timedelta(days=30 + r.randint(0, 150))
    return now + timedelta(days=r.randint(-20, 120))


def _create_time(i: int) -> datetime:
    r = random.Random(20000 + i)
    return datetime.now() - timedelta(days=10 + r.randint(0, 230))


def _pick_contacts(contacts, i: int):
    r = random.Random(30000 + i)
    extra = list(contacts[1:])
    r.shuffle(extra)
    return [contacts[0]] + extra[: r.randint(0, 2)]


def _pick_designers(designer_ids, i: int):
    r = random.Random(40000 + i)
    ids = list(designer_ids)
    r.shuffle(ids)
    return ids[: r.randint(1, 2)]


def _sample_value(label: str, ftype: str, opts) -> str:
    if ftype == "select":
        return opts[0] if opts else label
    if ftype == "text_multi":
        return f"{label}示例内容（多行测试）"
    return f"{label}示例值"


def _insert_test_data(db, admin_id: int) -> dict:
    depts = _dept_id_map(db)

    # 1) 客户单位（6 家）
    companies = []
    for name in COMPANIES:
        cat = CustomerCategory(category_name=f"{MARK}{name}")
        db.add(cat)
        db.flush()
        companies.append(cat)

    # 2) 对接人（每家 3 人，共 18 人）
    contacts_by_company = []
    ci = 0
    for cat in companies:
        lst = []
        for _ in range(3):
            nm = CONTACT_NAMES[ci]
            c = Customer(
                category_id=cat.id,
                customer_name=f"{MARK}{nm}",
                contact=f"138{ci:08d}",
                remark=f"{nm} 对接人",
            )
            db.add(c)
            db.flush()
            lst.append(c)
            ci += 1
        contacts_by_company.append(lst)

    # 3) 内部员工账号（5 个）
    designer_ids = []
    for username, real, dept, role in STAFF:
        u = SysUser(
            username=username,
            password=PASSWORD,
            real_name=f"{MARK}{real}",
            role=role,
            dept_id=depts.get(dept),
            is_enable=1,
        )
        db.add(u)
        db.flush()
        if username.startswith("test_designer"):
            designer_ids.append(u.id)

    # 4) 客户登录账号（每家 1 个，绑定客户单位）
    for idx, cat in enumerate(companies, start=1):
        db.add(
            SysUser(
                username=f"test_cs{idx}",
                password=PASSWORD,
                real_name=f"{MARK}客户·{COMPANIES[idx - 1]}",
                role="客户",
                category_id=cat.id,
                is_enable=1,
            )
        )
        db.flush()

    # 5) 30 个项目 + 对接人/设计师关联 + 节点/连线/表单值
    node_total = 0
    form_total = 0
    for i in range(30):
        c = i // 5
        cat = companies[c]
        contacts = contacts_by_company[c]
        archived = (i % 4 == 3)

        p = Project(
            project_name=f"{MARK}{SHORT[c]}·{PROJECT_NAMES[i]}",
            category_id=cat.id,
            customer_id=contacts[0].id,
            project_desc=f"{PROJECT_NAMES[i]}（测试项目，用于功能验证）",
            expect_time=_expect_time(i, archived),
            project_status="已归档" if archived else "进行中",
            create_user_id=admin_id,
            create_time=_create_time(i),
        )
        db.add(p)
        db.flush()

        for cc in _pick_contacts(contacts, i):
            db.add(ProjectContactRel(project_id=p.id, customer_id=cc.id))
        for d in _pick_designers(designer_ids, i):
            db.add(ProjectDesignerRel(project_id=p.id, user_id=d))

        flow = NODE_FLOWS[FLOW_ORDER[i % 3]]
        total = len(flow)
        progress = total if archived else (1 + (i % (total - 1)) if total > 1 else total)

        node_objs = []
        for si, (title, fields) in enumerate(flow, start=1):
            n = ProjectNode(
                project_id=p.id,
                node_title=title,
                node_remark=None,
                icon=None,
                sort=si,
                pos_x=Decimal((si - 1) * 220),
                pos_y=Decimal(0),
                create_user_id=admin_id,
            )
            db.add(n)
            db.flush()
            node_objs.append(n)
            node_total += 1

            if si <= progress:
                for label, ftype, opts in fields:
                    db.add(
                        ProjectNodeFormValue(
                            project_node_id=n.id,
                            template_node_form_id=None,
                            field_label=label,
                            field_type=ftype,
                            select_options=json.dumps(opts, ensure_ascii=False) if opts else None,
                            field_value=_sample_value(label, ftype, opts),
                            create_user_id=admin_id,
                        )
                    )
                    form_total += 1

        for a, b in zip(node_objs, node_objs[1:]):
            db.add(ProjectNodeEdge(project_id=p.id, source_node_id=a.id, target_node_id=b.id, label=None))

    return {"node": node_total, "form": form_total}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("  LINKOA 测试数据生成")
    print("=" * 60)
    print(f"数据库：{settings.DB_URL}")
    print("提示：建议先停止后端服务，避免 SQLite 被占用导致写入失败。\n")

    _ensure_schema()

    db = SessionLocal()
    try:
        admin_id = _ensure_baseline(db)

        # 先清后建（分两次提交，避免用户名/公司名唯一约束与插入冲突）
        cleaned = _clean_test_data(db)
        db.commit()
        cleaned_total = sum(v for v in cleaned.values() if isinstance(v, int))
        if cleaned_total > 0:
            print("[清理] 已清除旧测试数据：")
            for k, v in cleaned.items():
                if v:
                    print(f"        {k}：{v} 条")
        else:
            print("[清理] 未发现旧测试数据，跳过。")

        print("\n[生成] 正在写入全新测试数据 ...")
        stats = _insert_test_data(db, admin_id)
        db.commit()

        print("\n" + "=" * 60)
        print("  生成完成 ✔")
        print("=" * 60)
        print(f"客户单位：{len(COMPANIES)} 家")
        print(f"对接人：{len(COMPANIES) * 3} 人")
        print(f"内部员工账号：{len(STAFF)} 个")
        print(f"客户登录账号：{len(COMPANIES)} 个")
        print(f"项目：30 个（其中已归档 7 个、进行中 23 个）")
        print(f"项目节点：{stats['node']} 个")
        print(f"节点表单值：{stats['form']} 条")

        print("\n—— 测试账号（密码统一为 %s）——" % PASSWORD)
        print(f"  管理员：admin / admin123（系统初始账号）")
        for username, real, dept, role in STAFF:
            print(f"  {role}  {username}  {real}（{dept}）")
        for idx in range(len(COMPANIES)):
            print(f"  客户  test_cs{idx + 1}  【测试】客户·{COMPANIES[idx]}")

        print("\n说明：再次运行本脚本会自动清空旧测试数据并重建（= 恢复初始状态），不会重复堆叠。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
