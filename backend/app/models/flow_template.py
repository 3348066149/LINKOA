"""流程模板 4 张表：flow_template / flow_template_node / flow_template_node_edge / flow_template_node_form"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.timeutil import beijing_now


class FlowTemplate(Base):
    """流程模板：与项目全量值拷贝、深度解绑；删除模板不影响历史项目"""

    __tablename__ = "flow_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    template_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    create_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建人用户ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )


class FlowTemplateNode(Base):
    """模板节点：自由拓扑画布，带坐标；复制模板时值拷贝到 project_node"""

    __tablename__ = "flow_template_node"
    __table_args__ = (Index("idx_template_id", "template_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属模板ID")
    node_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联节点模板ID（表单定义来源，V1.3）")
    node_title: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点标题")
    node_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板节点备注")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="节点排序序号（用于列表展示顺序）")
    pos_x: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), comment="节点画布X坐标")
    pos_y: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), comment="节点画布Y坐标")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )


class FlowTemplateNodeEdge(Base):
    """模板节点连线：复制模板时值拷贝到 project_node_edge；整图提交全量覆盖"""

    __tablename__ = "flow_template_node_edge"
    __table_args__ = (
        Index("idx_template_id", "template_id"),
        Index("idx_source_target", "source_node_id", "target_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属模板ID")
    source_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="连线起始节点ID（关联 flow_template_node.id）")
    target_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="连线目标节点ID（关联 flow_template_node.id）")
    label: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="连线文字标签，可空")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")


class FlowTemplateNodeForm(Base):
    """模板节点表单定义：text_single / text_multi / select；项目实例仅填值不可改结构"""

    __tablename__ = "flow_template_node_form"
    __table_args__ = (Index("idx_template_node_id", "template_node_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    template_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联 flow_template_node.id")
    field_label: Mapped[str] = mapped_column(String(128), nullable=False, comment="表单显示名称")
    field_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="text_single单行 / text_multi多行 / select下拉单选")
    select_options: Mapped[str | None] = mapped_column(Text, nullable=True, comment="下拉选项JSON数组；非下拉存null")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="表单字段排序")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )
