"""客户满意度评价表 project_evaluation（V1.4.17）

一个项目一条客户评价，project_id 唯一；提交后一次性锁定，不可修改。
reflection 为内部反思/总结，客户永远不可见。
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectEvaluation(Base):
    __tablename__ = "project_evaluation"
    __table_args__ = (
        # 唯一约束：一个项目一条评价（DB 层锁定，service 层再 SELECT 二次校验）
        Index("uk_project_evaluation_project_id", "project_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="项目ID（project.id，唯一，一个项目一条评价）")
    design_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="设计满意度 1~5")
    service_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="服务响应速度 1~5")
    product_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="最终产品满意度 1~5")
    customer_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="客户备注（选填）")
    evaluate_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="评价人ID（sys_user.id，客户账号）")
    evaluate_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="评价时间")
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内部反思/总结（客户不可见）")
    reflection_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="反思编辑人ID")
    reflection_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="反思编辑时间")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
