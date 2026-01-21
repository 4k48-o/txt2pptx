"""
PPT Service API - PPT 生成服务路由模块
"""

from .router import router as ppt_router
from .files import router as ppt_files_router

__all__ = ["ppt_router", "ppt_files_router"]
