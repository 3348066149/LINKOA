"""V1.3 迁移：表单定义收口到节点模板库，新增 2 列（幂等，可重复执行）

运行：cd backend && python migrate_v13.py
- flow_template_node 新增 node_template_id（流程模板节点关联节点模板，表单定义来源）
- project_node_form_value 新增 select_options（冗余下拉选项，解决 select 字段选项丢失）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app.database import engine

STATEMENTS = [
    "ALTER TABLE flow_template_node ADD COLUMN node_template_id bigint DEFAULT NULL COMMENT '关联节点模板ID（表单定义来源）'",
    "ALTER TABLE project_node_form_value ADD COLUMN select_options text DEFAULT NULL COMMENT '冗余：下拉选项JSON数组'",
]


def main():
    with engine.begin() as conn:
        for sql in STATEMENTS:
            try:
                conn.execute(text(sql))
                print("OK   :", sql.split("ADD COLUMN")[1].strip().split()[0])
            except Exception as e:  # noqa: BLE001
                if "Duplicate column" in str(e):
                    print("SKIP :", sql.split("ADD COLUMN")[1].strip().split()[0], "(列已存在)")
                else:
                    raise


if __name__ == "__main__":
    main()
