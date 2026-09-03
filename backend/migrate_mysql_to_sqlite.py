"""MySQL → SQLite 数据迁移（V1.4 绿色便携化）

把本机 MySQL 的 linkoa 库全部数据迁移到 SQLite 库（路径从 backend/.env 的 DB_URL 读取）。
迁移后可直接删除 MySQL 库（或保留备份）。

运行：cd backend && python migrate_mysql_to_sqlite.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

from app.database import Base, prepare_sqlite_indexes
from app import models  # noqa: F401  触发模型注册

# MySQL 连接串：可用环境变量 LINKOA_MYSQL_URL 覆盖（换机器后无需改代码）
MYSQL_URL = os.environ.get(
    "LINKOA_MYSQL_URL",
    "mysql+pymysql://root:123456@localhost:3306/linkoa?charset=utf8mb4",
)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BACKEND_DIR, "uploads")
SQLITE_PATH = os.path.join(BACKEND_DIR, "linkoa.db")
def _load_sqlite_path():
    import io
    try:
        with io.open(os.path.join(BACKEND_DIR, ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DB_URL=sqlite:///"):
                    return line.split("sqlite:///", 1)[1]
    except OSError:
        pass
    return SQLITE_PATH
SQLITE_PATH = _load_sqlite_path()
SQLITE_URL = "sqlite:///" + SQLITE_PATH.replace("\\", "/")

# 迁移顺序：先父后子（本系统无外键约束，顺序其实不敏感）
TABLES = [
    "sys_user", "customer_category", "customer",
    "flow_template", "flow_template_node", "flow_template_node_edge", "flow_template_node_form",
    "project", "project_designer_rel", "project_node", "project_node_edge",
    "project_node_form_value", "attachment", "comment", "message",
    "node_template", "sys_operation_log",
]


def main():
    mysql_engine = create_engine(MYSQL_URL)
    sqlite_engine = create_engine(SQLITE_URL)

    prepare_sqlite_indexes()
    Base.metadata.drop_all(bind=sqlite_engine)   # 幂等：先清空旧表
    Base.metadata.create_all(bind=sqlite_engine)

    total = 0
    with mysql_engine.connect() as mconn:
        with sqlite_engine.begin() as sconn:
            for tname in TABLES:
                table = Base.metadata.tables[tname]
                rows = mconn.execute(text(f"SELECT * FROM {tname}")).mappings().all()
                if not rows:
                    print(f"  {tname}: 0 行")
                    continue
                cols = [c.name for c in table.columns]
                for row in rows:
                    data = {c: row[c] for c in cols if c in row}
                    # attachment.file_path 绝对路径 → 相对 uploads/ 的相对路径（便携化）
                    if tname == "attachment" and data.get("file_path"):
                        p = data["file_path"]
                        if os.path.isabs(p):
                            data["file_path"] = os.path.relpath(p, UPLOAD_ROOT)
                    sconn.execute(table.insert().values(**data))
                print(f"  {tname}: {len(rows)} 行")
                total += len(rows)

    print(f"\n迁移完成，共 {total} 行 → {SQLITE_PATH}")


if __name__ == "__main__":
    main()
