"""节点模板表 node_template：管理员预设的可复用节点类型，画布只能从节点模板库添加节点"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NodeTemplate(Base):
    __tablename__ = "node_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    node_title: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点类型名称")
    node_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="节点类型说明")
    icon: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="节点图标：预设图标组件名或 uploads/ 自定义图标路径（V1.4.3）")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="面板展示排序")
    form_fields: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="建议表单字段JSON数组：[{fieldLabel, fieldType, selectOptions, sort}]"
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
