"""AI 助手模块：AI 配置表 ai_config + 会话表 ai_conversation + 消息表 ai_message

V1.4.8 新增。设计要点：
- ai_config：单行配置（管理员面板可改），存人设 prompt / 模型 / Key / 生成参数。
- ai_conversation：按用户隔离，仿豆包/DeepSeek 左侧会话列表。
- ai_message：会话消息，role 为 user / assistant，sources 存来源项目引用（JSON 字符串）。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AiConfig(Base):
    """AI 配置（单行，运行时读 id 最小的那一条）：管理员面板可改，替换 .env 硬编码"""

    __tablename__ = "ai_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="AI 人设/职责 system prompt")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="deepseek-v4-flash", comment="模型名")
    api_key: Mapped[str] = mapped_column(String(256), nullable=False, default="", comment="API Key")
    base_url: Mapped[str] = mapped_column(String(256), nullable=False, default="https://api.deepseek.com", comment="接口地址")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7, comment="采样温度")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2048, comment="单次最大 token")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="最后更新人ID")


class AiConversation(Base):
    """AI 会话：每个用户拥有多个会话，删除会话级联删除其消息"""

    __tablename__ = "ai_conversation"
    __table_args__ = (Index("idx_ai_conv_user", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属用户ID")
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="新对话", comment="会话标题（首条消息截断）")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否置顶")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记（审计留痕，删除仅置位不物理删）")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class AiMessage(Base):
    """AI 消息：role 为 user / assistant；sources 存来源项目引用 JSON（[{id, projectName}]）"""

    __tablename__ = "ai_message"
    __table_args__ = (Index("idx_ai_msg_conv", "conversation_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    conversation_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属会话ID")
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="角色：user / assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    sources: Mapped[str | None] = mapped_column(Text, nullable=True, comment="来源引用 JSON 数组")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
