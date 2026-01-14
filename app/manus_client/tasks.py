"""
Async Task Manager - 异步任务管理模块
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from .client import AsyncManusClient
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class TaskStatus:
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AsyncTaskManager:
    """异步 Manus 任务管理器"""

    def __init__(
        self,
        client: AsyncManusClient,
        settings: Optional[Settings] = None,
    ):
        """
        初始化异步任务管理器

        Args:
            client: 异步 Manus API 客户端实例
            settings: 配置对象
        """
        self.client = client
        self._settings = settings or get_settings()

    async def create_task(
        self,
        prompt: str,
        attachments: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建新任务

        Args:
            prompt: 任务提示词
            attachments: 附件列表，格式: [{"filename": "xxx", "file_id": "xxx"}]
            project_id: 项目 ID（可选）

        Returns:
            创建的任务信息
        """
        logger.info(f"Creating task with prompt: {prompt[:50]}...")

        data: Dict[str, Any] = {"prompt": prompt}

        if attachments:
            data["attachments"] = attachments

        if project_id:
            data["project_id"] = project_id

        result = await self.client.post("/v1/tasks", data=data)

        # Manus API 返回 task_id，统一转换为 id
        task_id = result.get("task_id") or result.get("id")
        if task_id and "id" not in result:
            result["id"] = task_id
        
        logger.info(f"Task created: {task_id}")

        return result

    async def get_task(
        self,
        task_id: str,
        convert: bool = False,
    ) -> Dict[str, Any]:
        """
        获取任务详情

        Args:
            task_id: 任务 ID
            convert: 是否转换 pptx 输出

        Returns:
            任务详情
        """
        params = {"convert": "true"} if convert else None
        return await self.client.get(f"/v1/tasks/{task_id}", params=params)

    async def list_tasks(
        self,
        status: Optional[List[str]] = None,
        limit: int = 100,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取任务列表

        Args:
            status: 状态过滤，如 ["pending", "running"]
            limit: 返回数量限制
            project_id: 项目 ID 过滤

        Returns:
            任务列表
        """
        params: Dict[str, Any] = {"limit": limit}

        if status:
            params["status"] = status

        if project_id:
            params["project_id"] = project_id

        return await self.client.get("/v1/tasks", params=params)

    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """
        删除任务

        Args:
            task_id: 任务 ID

        Returns:
            删除结果
        """
        logger.info(f"Deleting task: {task_id}")
        return await self.client.delete(f"/v1/tasks/{task_id}")

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: Optional[int] = None,
        timeout: Optional[int] = None,
        convert: bool = True,
        on_status_change: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        异步轮询等待任务完成

        Args:
            task_id: 任务 ID
            poll_interval: 轮询间隔（秒），默认从配置读取
            timeout: 超时时间（秒），默认从配置读取
            convert: 完成后是否转换 pptx 格式（默认 True）
            on_status_change: 状态变化回调函数

        Returns:
            完成的任务详情

        Raises:
            TimeoutError: 超时
            RuntimeError: 任务失败
        """
        poll_interval = poll_interval or self._settings.poll_interval
        timeout = timeout or self._settings.poll_timeout

        logger.info(f"Waiting for task {task_id} to complete...")

        start_time = asyncio.get_event_loop().time()
        last_status = None

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")

            # 轮询时不需要 convert，只检查状态
            task = await self.get_task(task_id, convert=False)
            status = task.get("status")

            # 状态变化回调
            if status != last_status:
                logger.info(f"Task {task_id} status: {status} ({elapsed:.1f}s elapsed)")
                if on_status_change:
                    try:
                        await on_status_change(task_id, status, elapsed)
                    except Exception as e:
                        logger.warning(f"Status change callback error: {e}")
                last_status = status

            if status == TaskStatus.COMPLETED:
                logger.info(f"Task {task_id} completed successfully")
                # 完成后再次获取，使用 convert 参数
                if convert:
                    task = await self.get_task(task_id, convert=True)
                return task

            if status == TaskStatus.FAILED:
                error_msg = task.get("error", "Unknown error")
                raise RuntimeError(f"Task {task_id} failed: {error_msg}")

            await asyncio.sleep(poll_interval)

    async def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务进度信息

        Args:
            task_id: 任务 ID

        Returns:
            包含进度信息的字典
        """
        task = await self.get_task(task_id, convert=False)

        status = task.get("status", "unknown")
        outputs = task.get("output", [])
        credit_usage = task.get("credit_usage", 0)
        metadata = task.get("metadata", {})

        # 计算消息数量作为进度指标
        message_count = len(outputs)

        return {
            "task_id": task.get("id"),
            "status": status,
            "title": metadata.get("task_title"),
            "task_url": metadata.get("task_url"),
            "message_count": message_count,
            "credit_usage": credit_usage,
        }

