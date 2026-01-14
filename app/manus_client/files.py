"""
Async File Manager - 异步文件管理模块
"""

import logging
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path

import aiofiles
import httpx

from .client import AsyncManusClient
from ..exceptions import FileUploadException

logger = logging.getLogger(__name__)

# 文件大小限制 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class AsyncFileManager:
    """异步 Manus 文件管理器"""

    def __init__(self, client: AsyncManusClient):
        """
        初始化异步文件管理器

        Args:
            client: 异步 Manus API 客户端实例
        """
        self.client = client

    async def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        上传本地文件到 Manus（两步上传）

        Args:
            file_path: 本地文件路径

        Returns:
            包含 file_id 的响应

        Raises:
            FileNotFoundError: 文件不存在
            FileUploadException: 文件过大或上传失败
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise FileUploadException(
                f"File too large: {file_size} bytes",
                detail=f"Maximum file size is {MAX_FILE_SIZE} bytes (10MB)",
            )

        filename = path.name

        logger.info(f"Uploading file: {filename} ({file_size} bytes)")

        # Step 1: 创建文件记录，获取 presigned URL
        create_response = await self._create_file_record(filename)
        file_id = create_response.get("id")
        presigned_url = create_response.get("presigned_url")

        if not presigned_url:
            raise FileUploadException(
                "Failed to get presigned URL",
                detail="Manus API did not return presigned_url",
            )

        # Step 2: 读取文件并上传到 S3
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()

        await self._upload_to_s3(file_content, presigned_url)

        logger.info(f"File uploaded successfully: {file_id}")

        return {"file_id": file_id, "filename": filename, "size": file_size}

    async def upload_file_content(
        self,
        content: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """
        上传文件内容到 Manus

        Args:
            content: 文件内容（字节）
            filename: 文件名

        Returns:
            包含 file_id 的响应

        Raises:
            FileUploadException: 文件过大或上传失败
        """
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise FileUploadException(
                f"File too large: {file_size} bytes",
                detail=f"Maximum file size is {MAX_FILE_SIZE} bytes (10MB)",
            )

        logger.info(f"Uploading file content: {filename} ({file_size} bytes)")

        # Step 1: 创建文件记录
        create_response = await self._create_file_record(filename)
        file_id = create_response.get("id")
        presigned_url = create_response.get("presigned_url")

        if not presigned_url:
            raise FileUploadException(
                "Failed to get presigned URL",
                detail="Manus API did not return presigned_url",
            )

        # Step 2: 上传到 S3
        await self._upload_to_s3(content, presigned_url)

        logger.info(f"File uploaded successfully: {file_id}")

        return {"file_id": file_id, "filename": filename, "size": file_size}

    async def _create_file_record(self, filename: str) -> Dict[str, Any]:
        """创建文件记录"""
        return await self.client.post("/v1/files", data={"filename": filename})

    async def _upload_to_s3(self, content: bytes, presigned_url: str) -> None:
        """上传文件内容到 S3"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                response = await client.put(presigned_url, content=content)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise FileUploadException(
                "Failed to upload file to S3",
                detail=str(e),
            )

    async def list_files(self) -> Dict[str, Any]:
        """
        获取最近上传的文件列表

        Returns:
            文件列表
        """
        return await self.client.get("/v1/files")

    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        删除文件

        Args:
            file_id: 文件 ID

        Returns:
            删除结果
        """
        logger.info(f"Deleting file: {file_id}")
        return await self.client.delete(f"/v1/files/{file_id}")

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件详情

        Args:
            file_id: 文件 ID

        Returns:
            文件详情
        """
        return await self.client.get(f"/v1/files/{file_id}")

