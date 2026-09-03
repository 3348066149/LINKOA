"""SQLite → MySQL 数据迁移（反向迁移，V1.4 双数据库支持）

把 SQLite 库（路径取自 backend/.env 的 DB_URL，默认 backend/linkoa.db，随项目文件夹走）的数据迁移到 MySQL 的 linkoa 库（先清空目标表再写入）。
MySQL 建表前请先确保库已存在：CREATE DATABASE linkoa ...（或用 init.sql）。

运行：cd backend && python migrate_sqlite_to_mysql.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

from app.database import Base
from app import models  # noqa: F401  触发模型注册

# MySQL 连接串：可用环境变量 LINKOA_MYSQL_URL 覆盖（换机器后无需改代码）
MYSQL_URL = os.environ.get(
    "LINKOA_MYSQL_URL",
    "mysql+pymysql://root:123456@localhost:3306/linkoa?charset=utf8mb4",
)
# SQLite 路径从 backend/.env 的 DB_URL 读取（V1.4.3 起数据库文件为 app.db），兜底 backend/linkoa.db
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_URL = "sqlite:///" + os.path.join(BACKEND_DIR, "linkoa.db").replace("\\", "/")
def _load_sqlite_url():
    try:
        with io.open(os.path.join(BACKEND_DIR, ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DB_URL=sqlite:///"):
                    return "sqlite:///" + line.split("sqlite:///", 1)[1]
    except OSError:
        pass
    return SQLITE_URL
SQLITE_URL = _load_sqlite_url()

# 迁移顺序：先父后子（本系统无外键约束，顺序其实不敏感）
TABLES = [
    "sys_user", "customer_category", "customer",
    "flow_template", "flow_template_node", "flow_template_node_edge", "flow_template_node_form",
    "project", "project_designer_rel", "project_node", "project_node_edge",
    "project_node_form_value", "attachment", "comment", "message",
    "node_template", "sys_operation_log",
]


def main():
    sqlite_engine = create_engine(SQLITE_URL)
    mysql_engine = create_engine(MYSQL_URL)

    # MySQL 先清空再建表
    Base.metadata.drop_all(bind=mysql_engine)
    Base.metadata.create_all(bind=mysql_engine)

    total = 0
    with sqlite_engine.connect() as sconn:
        with mysql_engine.begin() as mconn:
            for tname in TABLES:
                table = Base.metadata.tables[tname]
                rows = sconn.execute(text(f"SELECT * FROM {tname}")).mappings().all()
                if not rows:
                    print(f"  {tname}: 0 行")
                    continue
                cols = [c.name for c in table.columns]
                for row in rows:
                    data = {c: row[c] for c in cols if c in row}
                    # file_path 已是相对 uploads/ 路径，get_download_info 兼容，无需转换
                    mconn.execute(table.insert().values(**data))
                print(f"  {tname}: {len(rows)} 行")
                total += len(rows)

    print(f"\n迁移完成，共 {total} 行 → MySQL linkoa 库")


if __name__ == "__main__":
    main()
