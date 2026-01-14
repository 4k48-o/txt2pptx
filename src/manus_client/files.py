"""
Manus File Manager - 文件管理模块
"""

import os
import requests
from typing import Optional, Dict, Any, BinaryIO
from .client import ManusClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 文件大小限制 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class FileManager:
    """Manus 文件管理器"""

    def __init__(self, client: ManusClient):
        """
        初始化文件管理器

        Args:
            client: Manus API 客户端实例
        """
        self.client = client

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        上传文件到 Manus（两步上传）

        Args:
            file_path: 本地文件路径

        Returns:
            包含 file_id 的响应

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件过大
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)")

        filename = os.path.basename(file_path)

        logger.info(f"Uploading file: {filename} ({file_size} bytes)")

        # Step 1: 创建文件记录，获取 presigned URL
        create_response = self._create_file_record(filename)
        file_id = create_response.get("id")
        presigned_url = create_response.get("presigned_url")

        if not presigned_url:
            raise RuntimeError("Failed to get presigned URL")

        # Step 2: 上传文件内容到 S3
        self._upload_to_s3(file_path, presigned_url)

        logger.info(f"File uploaded successfully: {file_id}")

        return {"file_id": file_id, "filename": filename}

    def upload_file_object(self, file_obj: BinaryIO, filename: str) -> Dict[str, Any]:
        """
        上传文件对象到 Manus

        Args:
            file_obj: 文件对象
            filename: 文件名

        Returns:
            包含 file_id 的响应
        """
        # 检查文件大小
        file_obj.seek(0, 2)  # 移到末尾
        file_size = file_obj.tell()
        file_obj.seek(0)  # 移回开头

        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)")

        logger.info(f"Uploading file object: {filename} ({file_size} bytes)")

        # Step 1: 创建文件记录
        create_response = self._create_file_record(filename)
        file_id = create_response.get("id")
        presigned_url = create_response.get("presigned_url")

        if not presigned_url:
            raise RuntimeError("Failed to get presigned URL")

        # Step 2: 上传到 S3
        self._upload_stream_to_s3(file_obj, presigned_url)

        logger.info(f"File uploaded successfully: {file_id}")

        return {"file_id": file_id, "filename": filename}

    def _create_file_record(self, filename: str) -> Dict[str, Any]:
        """创建文件记录"""
        return self.client.post("/v1/files", data={"filename": filename})

    def _upload_to_s3(self, file_path: str, presigned_url: str) -> None:
        """上传文件到 S3"""
        with open(file_path, "rb") as f:
            response = requests.put(presigned_url, data=f)
            response.raise_for_status()

    def _upload_stream_to_s3(self, file_obj: BinaryIO, presigned_url: str) -> None:
        """上传文件流到 S3"""
        response = requests.put(presigned_url, data=file_obj)
        response.raise_for_status()

    def list_files(self) -> Dict[str, Any]:
        """
        获取最近上传的文件列表

        Returns:
            文件列表
        """
        return self.client.get("/v1/files")

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        删除文件

        Args:
            file_id: 文件 ID

        Returns:
            删除结果
        """
        logger.info(f"Deleting file: {file_id}")
        return self.client.delete(f"/v1/files/{file_id}")

