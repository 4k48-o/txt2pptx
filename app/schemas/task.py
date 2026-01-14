"""
Task Schemas - 任务数据模型
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Manus API 任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LocalTaskStatus(str, Enum):
    """本地任务状态枚举（包含更细粒度的状态）"""

    PENDING = "pending"          # 等待处理
    UPLOADING = "uploading"      # 正在上传附件
    PROCESSING = "processing"    # Manus 正在处理
    DOWNLOADING = "downloading"  # 正在下载结果
    COMPLETED = "completed"      # 任务完成
    FAILED = "failed"            # 任务失败


class Attachment(BaseModel):
    """附件信息"""

    filename: str = Field(..., description="文件名")
    file_id: str = Field(..., description="文件 ID")


class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="任务提示词，描述要生成的 PPT 内容",
        examples=["创建一个关于人工智能发展趋势的PPT，包含5页"],
    )
    attachments: Optional[List[Attachment]] = Field(
        default=None,
        description="附件列表（可选）",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="项目 ID（可选）",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "创建一个关于人工智能发展趋势的PPT，要求专业、现代风格，包含5页",
                "attachments": [{"filename": "data.xlsx", "file_id": "file_xxx"}],
            }
        }


class TaskMetadata(BaseModel):
    """任务元数据"""

    task_title: Optional[str] = Field(default=None, description="任务标题")
    task_url: Optional[str] = Field(default=None, description="任务在线查看链接")


class OutputFile(BaseModel):
    """输出文件"""

    type: str = Field(..., description="输出类型")
    file_url: Optional[str] = Field(default=None, alias="fileUrl", description="文件下载链接")
    file_name: Optional[str] = Field(default=None, alias="fileName", description="文件名")


class TaskResponse(BaseModel):
    """任务响应"""

    id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    prompt: Optional[str] = Field(default=None, description="任务提示词")
    credit_usage: Optional[int] = Field(default=None, description="消耗的积分")
    metadata: Optional[TaskMetadata] = Field(default=None, description="任务元数据")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    
    # 原始输出数据（用于解析）
    output: Optional[List[Dict[str, Any]]] = Field(default=None, description="任务输出")
    
    # 解析后的 PPTX 下载链接
    pptx_url: Optional[str] = Field(default=None, description="PPTX 下载链接")
    pptx_filename: Optional[str] = Field(default=None, description="PPTX 文件名")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
        populate_by_name = True


class TaskListItem(BaseModel):
    """任务列表项"""

    id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    prompt: Optional[str] = Field(default=None, description="任务提示词")
    credit_usage: Optional[int] = Field(default=None, description="消耗的积分")
    metadata: Optional[TaskMetadata] = Field(default=None, description="任务元数据")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: List[TaskListItem] = Field(default_factory=list, description="任务列表")
    total: Optional[int] = Field(default=None, description="总数量")
    has_more: bool = Field(default=False, description="是否有更多")


class TaskProgressResponse(BaseModel):
    """任务进度响应"""

    task_id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    title: Optional[str] = Field(default=None, description="任务标题")
    task_url: Optional[str] = Field(default=None, description="任务在线查看链接")
    message_count: int = Field(default=0, description="处理消息数量")
    credit_usage: int = Field(default=0, description="消耗的积分")


class CreateTaskResponse(BaseModel):
    """创建任务响应"""

    id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    message: str = Field(default="Task created successfully", description="响应消息")

