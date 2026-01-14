"""
Manus Task Manager - 任务管理模块
"""

import time
from typing import Optional, List, Dict, Any
from .client import ManusClient
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus:
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskManager:
    """Manus 任务管理器"""

    def __init__(self, client: ManusClient):
        """
        初始化任务管理器

        Args:
            client: Manus API 客户端实例
        """
        self.client = client
        self.config = Config()

    def create_task(
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

        data = {"prompt": prompt}

        if attachments:
            data["attachments"] = attachments

        if project_id:
            data["project_id"] = project_id

        result = self.client.post("/v1/tasks", data=data)

        logger.info(f"Task created: {result.get('task_id', 'unknown')}")

        return result

    def get_task(self, task_id: str, convert: bool = False) -> Dict[str, Any]:
        """
        获取任务详情

        Args:
            task_id: 任务 ID
            convert: 是否转换 pptx 输出

        Returns:
            任务详情
        """
        params = {"convert": str(convert).lower()} if convert else None
        return self.client.get(f"/v1/tasks/{task_id}", params=params)

    def list_tasks(
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
        params = {"limit": limit}

        if status:
            params["status"] = status

        if project_id:
            params["project_id"] = project_id

        return self.client.get("/v1/tasks", params=params)

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """
        删除任务

        Args:
            task_id: 任务 ID

        Returns:
            删除结果
        """
        logger.info(f"Deleting task: {task_id}")
        return self.client.delete(f"/v1/tasks/{task_id}")

    def wait_for_completion(
        self,
        task_id: str,
        poll_interval: Optional[int] = None,
        timeout: Optional[int] = None,
        convert: bool = True,
    ) -> Dict[str, Any]:
        """
        轮询等待任务完成

        Args:
            task_id: 任务 ID
            poll_interval: 轮询间隔（秒），默认从配置读取
            timeout: 超时时间（秒），默认从配置读取
            convert: 完成后是否转换 pptx 格式（默认 True）

        Returns:
            完成的任务详情

        Raises:
            TimeoutError: 超时
            RuntimeError: 任务失败
        """
        poll_interval = poll_interval or self.config.poll_interval
        timeout = timeout or self.config.poll_timeout

        logger.info(f"Waiting for task {task_id} to complete...")

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")

            # 轮询时不需要 convert，只检查状态
            task = self.get_task(task_id, convert=False)
            status = task.get("status")

            logger.info(f"Task {task_id} status: {status} ({elapsed:.1f}s elapsed)")

            if status == TaskStatus.COMPLETED:
                logger.info(f"Task {task_id} completed successfully")
                # 完成后再次获取，使用 convert 参数
                if convert:
                    task = self.get_task(task_id, convert=True)
                return task

            if status == TaskStatus.FAILED:
                error_msg = task.get("error", "Unknown error")
                raise RuntimeError(f"Task {task_id} failed: {error_msg}")

            time.sleep(poll_interval)

