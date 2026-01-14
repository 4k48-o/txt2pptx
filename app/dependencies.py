"""
Dependency Injection - 依赖注入
"""

from typing import AsyncGenerator, Optional
from functools import lru_cache

from .config import Settings, get_settings
from .manus_client import AsyncManusClient, AsyncTaskManager, AsyncFileManager
from .services import TaskTrackerService, PPTGeneratorService


async def get_settings_dep() -> Settings:
    """获取配置依赖"""
    return get_settings()


# 全局单例实例
_manus_client: Optional[AsyncManusClient] = None
_task_tracker: Optional[TaskTrackerService] = None
_ppt_generator: Optional[PPTGeneratorService] = None


async def get_manus_client() -> AsyncGenerator[AsyncManusClient, None]:
    """
    获取 Manus 客户端依赖

    使用全局单例，避免每次请求创建新连接
    """
    global _manus_client

    if _manus_client is None:
        _manus_client = AsyncManusClient()

    yield _manus_client


async def get_task_manager() -> AsyncTaskManager:
    """获取任务管理器依赖"""
    global _manus_client
    
    if _manus_client is None:
        _manus_client = AsyncManusClient()

    return AsyncTaskManager(_manus_client)


async def get_file_manager() -> AsyncFileManager:
    """获取文件管理器依赖"""
    global _manus_client
    
    if _manus_client is None:
        _manus_client = AsyncManusClient()

    return AsyncFileManager(_manus_client)


def get_task_tracker() -> TaskTrackerService:
    """获取任务追踪服务依赖"""
    global _task_tracker

    if _task_tracker is None:
        _task_tracker = TaskTrackerService()

    return _task_tracker


async def get_ppt_generator() -> PPTGeneratorService:
    """获取 PPT 生成服务依赖"""
    global _ppt_generator, _manus_client, _task_tracker

    if _manus_client is None:
        _manus_client = AsyncManusClient()

    if _task_tracker is None:
        _task_tracker = TaskTrackerService()

    if _ppt_generator is None:
        _ppt_generator = PPTGeneratorService(
            client=_manus_client,
            tracker=_task_tracker,
        )

    return _ppt_generator


async def cleanup_manus_client() -> None:
    """清理 Manus 客户端连接"""
    global _manus_client
    if _manus_client:
        await _manus_client.close()
        _manus_client = None
