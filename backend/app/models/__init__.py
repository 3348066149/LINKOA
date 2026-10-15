"""ORM 模型统一导出（18 张表 + V1.4.8 AI 助手 3 张表 + V1.4.17 客户满意度评价）"""
from app.models.ai import AiConfig, AiConversation, AiMessage
from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.customer import Customer, CustomerCategory
from app.models.dept import SysDept
from app.models.evaluation import ProjectEvaluation
from app.models.flow_template import (
    FlowTemplate,
    FlowTemplateNode,
    FlowTemplateNodeEdge,
    FlowTemplateNodeForm,
)
from app.models.message import Message
from app.models.node_template import NodeTemplate
from app.models.project import Project, ProjectContactRel, ProjectDesignerRel
from app.models.project_node import ProjectNode, ProjectNodeEdge, ProjectNodeFormValue
from app.models.project_stage import ProjectStage
from app.models.role import SysRole
from app.models.sys_operation_log import SysOperationLog
from app.models.user import SysUser

__all__ = [
    "AiConfig",
    "AiConversation",
    "AiMessage",
    "SysUser",
    "SysRole",
    "SysDept",
    "CustomerCategory",
    "Customer",
    "FlowTemplate",
    "FlowTemplateNode",
    "FlowTemplateNodeEdge",
    "FlowTemplateNodeForm",
    "Project",
    "ProjectDesignerRel",
    "ProjectContactRel",
    "ProjectNode",
    "ProjectNodeEdge",
    "ProjectNodeFormValue",
    "ProjectStage",
    "ProjectEvaluation",
    "Attachment",
    "Comment",
    "Message",
    "NodeTemplate",
    "SysOperationLog",
]
