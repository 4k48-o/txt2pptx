"""
PPT Generator Service - PPT 生成服务

后台任务处理：创建任务、轮询状态、下载结果
"""

import logging
from typing import Optional, List, Dict, Any, Callable, Awaitable
from pathlib import Path
from datetime import datetime

import httpx
import aiofiles

from ..schemas import LocalTaskStatus
from ..config import Settings, get_settings
from ..manus_client import AsyncManusClient, AsyncTaskManager, AsyncFileManager
from .task_tracker import TaskTrackerService, LocalTask

logger = logging.getLogger(__name__)


# 状态变化回调类型
StatusCallback = Callable[[str, str, float], Awaitable[None]]


class PPTGeneratorService:
    """PPT 生成服务"""

    def __init__(
        self,
        client: AsyncManusClient,
        tracker: TaskTrackerService,
        settings: Optional[Settings] = None,
    ):
        """
        初始化 PPT 生成服务

        Args:
            client: Manus API 客户端
            tracker: 本地任务追踪服务
            settings: 配置对象
        """
        self.client = client
        self.task_manager = AsyncTaskManager(client)
        self.file_manager = AsyncFileManager(client)
        self.tracker = tracker
        self._settings = settings or get_settings()

        logger.info("PPTGeneratorService initialized")

    async def generate_ppt(
        self,
        local_task_id: str,
        on_status_change: Optional[StatusCallback] = None,
    ) -> LocalTask:
        """
        生成 PPT（后台任务入口）

        完整流程:
        1. 获取本地任务
        2. 上传附件（如有）
        3. 创建 Manus 任务
        4. 轮询等待完成
        5. 下载 PPTX 文件
        6. 更新本地任务状态

        Args:
            local_task_id: 本地任务 ID
            on_status_change: 状态变化回调

        Returns:
            更新后的本地任务
        """
        logger.info(f"Starting PPT generation for task: {local_task_id}")

        try:
            # 1. 获取本地任务
            local_task = await self.tracker.get(local_task_id)
            if not local_task:
                raise ValueError(f"Task not found: {local_task_id}")

            # 2. 上传附件
            attachments = await self._upload_attachments(local_task_id, local_task.attachments)

            # 3. 创建 Manus 任务
            await self.tracker.update(
                local_task_id,
                status=LocalTaskStatus.PROCESSING.value,
            )

            manus_task = await self.task_manager.create_task(
                prompt=local_task.prompt,
                attachments=attachments if attachments else None,
            )

            manus_task_id = manus_task.get("id") or manus_task.get("task_id")
            # Manus API 直接返回 task_title 和 task_url
            task_title = manus_task.get("task_title") or manus_task.get("metadata", {}).get("task_title")
            task_url = manus_task.get("task_url") or manus_task.get("metadata", {}).get("task_url")

            await self.tracker.update(
                local_task_id,
                manus_task_id=manus_task_id,
                title=task_title,
                task_url=task_url,
            )

            logger.info(f"Manus task created: {manus_task_id}")

            # 4. 轮询等待完成
            async def status_callback(task_id: str, status: str, elapsed: float):
                """状态变化回调"""
                if on_status_change:
                    await on_status_change(local_task_id, status, elapsed)

            completed_task = await self.task_manager.wait_for_completion(
                manus_task_id,
                convert=True,
                on_status_change=status_callback,
            )

            # 5. 提取 PPTX URL 并下载
            pptx_url, pptx_filename = self._extract_pptx_info(completed_task)

            if pptx_url:
                await self.tracker.update(
                    local_task_id,
                    status=LocalTaskStatus.DOWNLOADING.value,
                    pptx_url=pptx_url,
                    pptx_filename=pptx_filename,
                    credit_usage=completed_task.get("credit_usage", 0),
                )

                local_file_path = await self._download_pptx(
                    local_task_id,
                    pptx_url,
                    pptx_filename,
                )

                # 6. 完成
                return await self.tracker.update(
                    local_task_id,
                    status=LocalTaskStatus.COMPLETED.value,
                    local_file_path=local_file_path,
                )
            else:
                # 没有 PPTX URL，但任务完成
                logger.warning(f"No PPTX URL found for task: {local_task_id}")
                return await self.tracker.update(
                    local_task_id,
                    status=LocalTaskStatus.COMPLETED.value,
                    credit_usage=completed_task.get("credit_usage", 0),
                )

        except TimeoutError as e:
            logger.error(f"Task timeout: {local_task_id}, {e}")
            return await self.tracker.update(
                local_task_id,
                status=LocalTaskStatus.FAILED.value,
                error=f"Task timeout: {str(e)}",
            )

        except Exception as e:
            logger.error(f"Task failed: {local_task_id}, {e}")
            return await self.tracker.update(
                local_task_id,
                status=LocalTaskStatus.FAILED.value,
                error=str(e),
            )

    async def _upload_attachments(
        self,
        local_task_id: str,
        attachments: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        上传附件到 Manus

        Args:
            local_task_id: 本地任务 ID
            attachments: 附件列表 [{"filename": "xxx", "file_path": "xxx"}]

        Returns:
            上传后的附件列表 [{"filename": "xxx", "file_id": "xxx"}]
        """
        if not attachments:
            return []

        await self.tracker.update(
            local_task_id,
            status=LocalTaskStatus.UPLOADING.value,
        )

        uploaded = []
        for attachment in attachments:
            file_path = attachment.get("file_path")
            filename = attachment.get("filename")

            if file_path:
                # 上传本地文件
                result = await self.file_manager.upload_file(file_path)
                uploaded.append({
                    "filename": result["filename"],
                    "file_id": result["file_id"],
                })
            elif attachment.get("file_id"):
                # 已有 file_id，直接使用
                uploaded.append({
                    "filename": filename,
                    "file_id": attachment["file_id"],
                })

        logger.info(f"Uploaded {len(uploaded)} attachments for task: {local_task_id}")
        return uploaded

    def _extract_pptx_info(
        self,
        task: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str]]:
        """
        从任务响应中提取 PPTX 下载信息

        Args:
            task: Manus 任务响应

        Returns:
            (pptx_url, pptx_filename)
        """
        outputs = task.get("output", [])
        
        for output_item in outputs:
            if output_item.get("type") == "message":
                for content_item in output_item.get("content", []):
                    if content_item.get("type") == "output_file":
                        file_url = content_item.get("fileUrl")
                        file_name = content_item.get("fileName")
                        
                        if file_url and (file_url.endswith(".pptx") or "pptx" in file_url.lower()):
                            return file_url, file_name

        return None, None

    async def _download_pptx(
        self,
        local_task_id: str,
        pptx_url: str,
        pptx_filename: Optional[str] = None,
    ) -> str:
        """
        下载 PPTX 文件到本地

        Args:
            local_task_id: 本地任务 ID
            pptx_url: PPTX 下载链接
            pptx_filename: 文件名

        Returns:
            本地文件路径
        """
        # 生成文件名，确保有 .pptx 扩展名
        if not pptx_filename:
            pptx_filename = f"ppt_{local_task_id[:8]}.pptx"
        elif not pptx_filename.lower().endswith('.pptx'):
            pptx_filename = f"{pptx_filename}.pptx"

        # 确保输出目录存在
        output_dir = Path(self._settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        local_path = output_dir / pptx_filename

        logger.info(f"Downloading PPTX: {pptx_url} -> {local_path}")

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await client.get(pptx_url)
            response.raise_for_status()

            async with aiofiles.open(local_path, "wb") as f:
                await f.write(response.content)

        logger.info(f"Downloaded PPTX: {local_path} ({len(response.content)} bytes)")
        return str(local_path)

