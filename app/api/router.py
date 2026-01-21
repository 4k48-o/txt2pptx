"""
API Router - 主路由配置

三服务架构：
- PPT 服务: /api/ppt/*
- 视频服务: /api/video/*
- 爬虫服务: /api/crawler/*
"""

from fastapi import APIRouter

from .health import router as health_router

# 导入三个服务的路由
from .ppt import ppt_router, ppt_files_router
from .video import video_router
from .crawler import crawler_router
from .test import router as test_router

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册全局路由
api_router.include_router(health_router)

# 注册服务路由
api_router.include_router(ppt_router)  # PPT 服务任务路由
api_router.include_router(ppt_files_router)  # PPT 服务文件路由
api_router.include_router(video_router)  # 视频服务路由
api_router.include_router(crawler_router)  # 爬虫服务路由
api_router.include_router(test_router)  # 测试路由（历史数据回放）

