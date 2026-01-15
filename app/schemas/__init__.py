"""
Pydantic Schemas - 数据模型定义
"""

from .common import APIResponse, ErrorResponse, PaginationInfo
from .task import (
    CreateTaskRequest,
    TaskResponse,
    TaskListResponse,
    TaskListItem,
    TaskProgressResponse,
    TaskDetailResponse,
    TaskFile,
    TaskStatus,
    LocalTaskStatus,
    CreateTaskResponse,
)
from .file import (
    FileUploadResponse,
    FileListResponse,
    FileResponse,
    FileDeleteResponse,
)

__all__ = [
    # Common
    "APIResponse",
    "ErrorResponse",
    "PaginationInfo",
    # Task
    "CreateTaskRequest",
    "CreateTaskResponse",
    "TaskResponse",
    "TaskListResponse",
    "TaskListItem",
    "TaskProgressResponse",
    "TaskDetailResponse",
    "TaskFile",
    "TaskStatus",
    "LocalTaskStatus",
    # File
    "FileUploadResponse",
    "FileListResponse",
    "FileResponse",
    "FileDeleteResponse",
]

