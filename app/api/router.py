"""
API Router - 主路由配置
"""

from fastapi import APIRouter

from .health import router as health_router
from .tasks import router as tasks_router
from .tasks_v2 import router as tasks_v2_router
from .files import router as files_router
from .video import router as video_router

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(tasks_v2_router)  # Webhook 模式 API
api_router.include_router(files_router)
api_router.include_router(video_router)  # 视频生成 API

