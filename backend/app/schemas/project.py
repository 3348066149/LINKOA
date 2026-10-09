"""项目基础 DTO（Api.md 第 7 章；V1.4.7 客户单位/对接人结构）"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, PageQuery
from app.schemas.evaluation import EvaluationPublicOut


class ProjectCreateRequest(CamelModel):
    project_name: str = Field(..., min_length=1, max_length=256)
    category_id: int = Field(..., gt=0)  # 归属客户单位（customer_category.id）
    contact_customer_ids: list[int] = Field(..., min_length=1)  # 客户对接人（单位下的 customer，至少 1 人）
    project_desc: str | None = None
    start_time: datetime | None = None  # 项目开始时间（可编辑）
    expect_time: datetime | None = None
    create_time: datetime | None = None  # 立项时间（=创建时间）；不传默认当前时间，支持补录历史项目
    designer_rel_user_id_list: list[int] = []
    template_id: int | None = None  # 不为空时执行模板实例化


class ProjectListQuery(PageQuery):
    project_name: str | None = None  # 模糊搜索
    category_id: int | None = None  # 按客户单位筛选
    project_status: Literal["进行中", "已归档"] | None = None
    create_time_start: datetime | None = None  # 立项时间范围起（含）
    create_time_end: datetime | None = None  # 立项时间范围止（含）


class ProjectUpdateBaseRequest(CamelModel):
    id: int = Field(..., gt=0)
    project_name: str = Field(..., min_length=1, max_length=256)
    category_id: int = Field(..., gt=0)
    contact_customer_ids: list[int] = Field(..., min_length=1)  # 全量覆盖（先删后插）
    project_desc: str | None = None
    start_time: datetime | None = None  # 项目开始时间（可编辑）
    expect_time: datetime | None = None
    create_time: datetime | None = None  # 立项时间（=创建时间），传则更新，不传保留原值
    designer_rel_user_id_list: list[int] = []  # 全量覆盖（先删后插）


class ProjectIdRequest(CamelModel):
    """归档 / 取消归档 / 删除项目入参"""

    project_id: int = Field(..., gt=0)


# ---- 出参 ----

class ProjectListItem(CamelModel):
    id: int
    project_name: str
    category_id: int | None = None  # 归属客户单位ID
    company_name: str | None = None  # 客户单位名称（原"客户"概念）
    customer_id: int  # 首位对接人ID（兼容保留）
    customer_name: str | None = None  # 首位对接人姓名（兼容保留）
    contact_names: str = ""  # 全部客户对接人，顿号分隔
    designer_names: str = ""  # 全部我方设计师，顿号分隔
    create_time: datetime | None = None  # 立项时间（=创建时间）
    start_time: datetime | None = None  # 项目开始时间
    expect_time: datetime | None = None  # 预计结束时间（卡片倒计时用）
    cover_image: str | None = None  # 卡片封面图相对路径
    project_status: str
    progress_percent: int = 0  # 节点进度占比（已填表单节点/全部节点），内部用
    evaluation: EvaluationPublicOut | None = None  # 客户评价（公开字段，已评价才非空）


class DesignerItem(CamelModel):
    user_id: int
    real_name: str


class ContactItem(CamelModel):
    """客户对接人（客户单位下的 customer 条目）"""

    customer_id: int
    customer_name: str


class ProjectNodeBrief(CamelModel):
    id: int
    node_title: str
    node_remark: str | None = None
    icon: str | None = None  # 节点图标（预设图标名或 uploads/ 路径，V1.4.3）
    sort: int
    pos_x: Decimal
    pos_y: Decimal
    has_form: bool = False
    form_filled: bool = False
    attachment_count: int = 0
    create_time: datetime | None = None  # 节点创建时间
    update_time: datetime | None = None  # 节点最后更新时间


class ProjectEdgeOut(CamelModel):
    id: int
    source_node_id: int
    target_node_id: int
    label: str | None = None


class ProjectDetail(CamelModel):
    id: int
    project_name: str
    category_id: int | None = None  # 归属客户单位ID
    company_name: str | None = None  # 客户单位名称
    customer_id: int  # 首位对接人ID（兼容保留）
    customer_name: str | None = None  # 首位对接人姓名（兼容保留）
    project_desc: str | None = None
    start_time: datetime | None = None  # 项目开始时间
    expect_time: datetime | None = None  # 预计结束时间
    cover_image: str | None = None  # 卡片封面图相对路径
    project_status: str
    create_user_name: str | None = None
    create_time: datetime | None = None  # 立项时间
    designer_list: list[DesignerItem] = []
    contact_list: list[ContactItem] = []  # 全部客户对接人
    nodes: list[ProjectNodeBrief] = []
    edges: list[ProjectEdgeOut] = []
    evaluation: EvaluationPublicOut | None = None  # 客户评价（公开字段；反思走内部 GET /api/evaluation/{projectId}）
