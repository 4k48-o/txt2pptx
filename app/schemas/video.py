"""
Video Schemas - 视频生成数据模型
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class VideoTaskStatus(str, Enum):
    """视频任务状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoTaskRequest(BaseModel):
    """视频生成任务请求"""

    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="视频主题（用户输入的文本描述）",
        examples=["Introduction to Artificial Intelligence"],
    )
    duration: int = Field(
        ...,
        ge=5,
        le=30,
        description="视频时长（秒），前端用户选择",
        examples=[15],
    )
    style: str = Field(
        ...,
        description="视频风格，前端用户选择",
        examples=["educational"],
    )
    target_audience: str = Field(
        ...,
        description="目标受众，前端用户选择",
        examples=["general"],
    )
    client_id: Optional[str] = Field(
        default=None,
        description="WebSocket 客户端 ID（可选）",
    )


class VideoTaskResponse(BaseModel):
    """视频生成任务响应"""

    task_id: str = Field(..., description="任务 ID")
    status: VideoTaskStatus = Field(..., description="任务状态")
    step: Optional[str] = Field(
        default=None,
        description="当前步骤（script_generation / video_generation）",
    )
    video_url: Optional[str] = Field(
        default=None,
        description="视频下载链接（任务完成后可用）",
    )
    markdown_url: Optional[str] = Field(
        default=None,
        description="Markdown 文件下载链接（任务完成后可用）",
    )
    message: Optional[str] = Field(
        default=None,
        description="状态消息",
    )
