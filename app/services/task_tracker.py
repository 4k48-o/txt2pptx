"""
Task Tracker Service - 本地任务追踪服务

使用 JSON 文件存储任务状态，支持异步 CRUD 操作
"""

import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from uuid import uuid4

import aiofiles

from ..schemas import LocalTaskStatus
from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LocalTask:
    """本地任务数据结构"""

    id: str                                    # 本地任务 ID
    manus_task_id: Optional[str] = None        # Manus 任务 ID
    prompt: str = ""                           # 任务提示词
    status: str = LocalTaskStatus.PENDING.value  # 任务状态
    error: Optional[str] = None                # 错误信息
    
    # 文件相关
    attachments: List[Dict[str, str]] = field(default_factory=list)  # 附件列表
    pptx_url: Optional[str] = None             # PPTX 下载链接
    pptx_filename: Optional[str] = None        # PPTX 文件名
    local_file_path: Optional[str] = None      # 本地保存路径
    
    # 元数据
    title: Optional[str] = None                # 任务标题
    task_url: Optional[str] = None             # Manus 任务链接
    credit_usage: int = 0                      # 消耗积分
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalTask":
        """从字典创建"""
        return cls(**data)


class TaskTrackerService:
    """本地任务追踪服务"""

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化任务追踪服务

        Args:
            storage_path: 存储文件路径，默认从配置读取
        """
        settings = get_settings()
        
        if storage_path:
            self._storage_path = Path(storage_path)
        else:
            self._storage_path = Path(settings.output_dir) / "tasks.json"
        
        self._lock = asyncio.Lock()
        self._ensure_storage_dir()

        logger.info(f"TaskTrackerService initialized, storage: {self._storage_path}")

    def _ensure_storage_dir(self) -> None:
        """确保存储目录存在"""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化空的 JSON 文件
        if not self._storage_path.exists():
            self._storage_path.write_text("{}")

    async def _load_tasks(self) -> Dict[str, Dict[str, Any]]:
        """加载所有任务"""
        try:
            async with aiofiles.open(self._storage_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content) if content else {}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    async def _save_tasks(self, tasks: Dict[str, Dict[str, Any]]) -> None:
        """保存所有任务"""
        async with aiofiles.open(self._storage_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(tasks, ensure_ascii=False, indent=2))

    async def create(
        self,
        prompt: str,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> LocalTask:
        """
        创建新任务

        Args:
            prompt: 任务提示词
            attachments: 附件列表

        Returns:
            创建的本地任务
        """
        task = LocalTask(
            id=str(uuid4()),
            prompt=prompt,
            attachments=attachments or [],
        )

        async with self._lock:
            tasks = await self._load_tasks()
            tasks[task.id] = task.to_dict()
            await self._save_tasks(tasks)

        logger.info(f"Created local task: {task.id}")
        return task

    async def get(self, task_id: str) -> Optional[LocalTask]:
        """
        获取任务

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，不存在返回 None
        """
        async with self._lock:
            tasks = await self._load_tasks()
            task_data = tasks.get(task_id)
            
        if task_data:
            return LocalTask.from_dict(task_data)
        return None

    async def update(
        self,
        task_id: str,
        **kwargs,
    ) -> Optional[LocalTask]:
        """
        更新任务

        Args:
            task_id: 任务 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的任务，不存在返回 None
        """
        async with self._lock:
            tasks = await self._load_tasks()
            task_data = tasks.get(task_id)
            
            if not task_data:
                return None
            
            # 更新字段
            task_data.update(kwargs)
            task_data["updated_at"] = datetime.utcnow().isoformat()
            
            # 如果状态变为完成，记录完成时间
            if kwargs.get("status") == LocalTaskStatus.COMPLETED.value:
                task_data["completed_at"] = datetime.utcnow().isoformat()
            
            tasks[task_id] = task_data
            await self._save_tasks(tasks)
        
        logger.debug(f"Updated task {task_id}: {list(kwargs.keys())}")
        return LocalTask.from_dict(task_data)

    async def list(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LocalTask]:
        """
        获取任务列表

        Args:
            status: 状态过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            任务列表
        """
        async with self._lock:
            tasks = await self._load_tasks()
        
        # 转换为列表并排序（按创建时间倒序）
        task_list = [LocalTask.from_dict(t) for t in tasks.values()]
        task_list.sort(key=lambda x: x.created_at, reverse=True)
        
        # 状态过滤
        if status:
            task_list = [t for t in task_list if t.status == status]
        
        # 分页
        return task_list[offset : offset + limit]

    async def delete(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务 ID

        Returns:
            是否删除成功
        """
        async with self._lock:
            tasks = await self._load_tasks()
            
            if task_id not in tasks:
                return False
            
            del tasks[task_id]
            await self._save_tasks(tasks)
        
        logger.info(f"Deleted task: {task_id}")
        return True

    async def count(self, status: Optional[str] = None) -> int:
        """
        获取任务数量

        Args:
            status: 状态过滤

        Returns:
            任务数量
        """
        async with self._lock:
            tasks = await self._load_tasks()
        
        if status:
            return sum(1 for t in tasks.values() if t.get("status") == status)
        return len(tasks)

