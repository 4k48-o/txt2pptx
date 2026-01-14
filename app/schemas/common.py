"""
Common Schemas - 通用数据模型
"""

from typing import TypeVar, Generic, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """通用 API 响应包装"""

    success: bool = Field(default=True, description="请求是否成功")
    data: Optional[T] = Field(default=None, description="响应数据")
    message: Optional[str] = Field(default=None, description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间戳")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = Field(default=False, description="请求是否成功")
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(default=None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间戳")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PaginationInfo(BaseModel):
    """分页信息"""

    total: int = Field(..., description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
    has_more: bool = Field(default=False, description="是否有更多数据")

