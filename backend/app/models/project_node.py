"""项目画布 3 张表：project_node / project_node_edge / project_node_form_value"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectNode(Base):
    """项目画布节点：从模板值拷贝生成；删除时级联删出入连线与表单值；临时新增节点无表单"""

    __tablename__ = "project_node"
    __table_args__ = (Index("idx_project_id", "project_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属项目ID")
    node_title: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点标题")
    node_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="节点备注")
    icon: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="节点图标（从模板冗余拷贝，V1.4.3）")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="节点排序序号")
    pos_x: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), comment="节点画布X坐标")
    pos_y: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), comment="节点画布Y坐标")
    create_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建人ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class ProjectNodeEdge(Base):
    """项目节点连线：模板拷贝时需节点ID重映射；删除节点时级联删 source/target 连线"""

    __tablename__ = "project_node_edge"
    __table_args__ = (
        Index("idx_project_id", "project_id"),
        Index("idx_source_target", "source_node_id", "target_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属项目ID")
    source_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="连线起始节点ID（关联 project_node.id）")
    target_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="连线目标节点ID（关联 project_node.id）")
    label: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="连线文字标签，可空")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")


class ProjectNodeFormValue(Base):
    """项目节点表单填写值：冗余 field_label/field_type 防模板修改破坏历史；全量覆盖保存"""

    __tablename__ = "project_node_form_value"
    __table_args__ = (Index("idx_project_node_id", "project_node_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联 project_node.id")
    template_node_form_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="来源模板表单ID，仅溯源用")
    field_label: Mapped[str] = mapped_column(String(128), nullable=False, comment="冗余：表单显示名称")
    field_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="冗余：字段类型")
    select_options: Mapped[str | None] = mapped_column(Text, nullable=True, comment="冗余：下拉选项JSON数组（V1.3）")
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户填写内容")
    create_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="填写人ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
