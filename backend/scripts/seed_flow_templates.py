"""预置流程模板 + 「布展搭建」节点类型（幂等，薄封装）。

核心逻辑已沉淀到 app.services.template_service.init_default_flow_templates，
后端启动时会自动初始化；本脚本仅保留手动触发的入口：
打开 SessionLocal → 调用 service 同一函数 → 打印汇总（避免双份逻辑）。

运行（任意 CWD 均可）：
  ../.venv/Scripts/python.exe backend/scripts/seed_flow_templates.py
  或 cd backend && ../.venv/Scripts/python.exe scripts/seed_flow_templates.py
"""
import os
import sys

# 脚本位于 backend/scripts/，app 包在 backend/ 下，把 backend/ 加入 sys.path，
# 保证无论从哪个 CWD 启动都能 `from app.database import SessionLocal`。
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import func, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import FlowTemplate, NodeTemplate  # noqa: E402
from app.services import template_service  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        template_service.init_default_flow_templates(db)

        flow_total = db.execute(select(func.count(FlowTemplate.id))).scalar_one()
        node_total = db.execute(select(func.count(NodeTemplate.id))).scalar_one()
        print(f"[汇总] 流程模板初始化完成（幂等）：flow_template 总数 {flow_total}，node_template 总数 {node_total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
