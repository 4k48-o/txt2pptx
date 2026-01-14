"""
File Schemas - 文件数据模型
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class FileResponse(BaseModel):
    """文件响应"""

    id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    size: Optional[int] = Field(default=None, description="文件大小（字节）")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class FileUploadRequest(BaseModel):
    """文件上传请求（用于表单验证）"""

    filename: str = Field(..., description="文件名")


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    file_id: str = Field(..., description="文件 ID")
    filename: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小（字节）")
    message: str = Field(default="File uploaded successfully", description="响应消息")


class FileListResponse(BaseModel):
    """文件列表响应"""

    files: List[FileResponse] = Field(default_factory=list, description="文件列表")
    total: Optional[int] = Field(default=None, description="总数量")


class FileDeleteResponse(BaseModel):
    """文件删除响应"""

    file_id: str = Field(..., description="文件 ID")
    message: str = Field(default="File deleted successfully", description="响应消息")

