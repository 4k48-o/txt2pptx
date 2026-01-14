"""
API Router - 主路由配置
"""

from fastapi import APIRouter

from .health import router as health_router
from .tasks import router as tasks_router
from .files import router as files_router

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(files_router)

