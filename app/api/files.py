"""
Files API - 文件管理路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..schemas import (
    APIResponse,
    FileUploadResponse,
    FileListResponse,
    FileResponse,
)
from ..schemas.file import FileDeleteResponse
from ..manus_client import AsyncFileManager
from ..dependencies import get_file_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 文件大小限制 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post(
    "/upload",
    response_model=APIResponse[FileUploadResponse],
    summary="上传参考文件",
    description="上传文件到 Manus，返回 file_id 用于创建任务时附加",
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    file_manager: AsyncFileManager = Depends(get_file_manager),
):
    """
    上传参考文件

    - 接收 multipart/form-data
    - 文件大小限制 10MB
    - 返回 file_id 用于创建任务时附加
    """
    # 检查文件大小
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size} bytes, max {MAX_FILE_SIZE} bytes (10MB)",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file not allowed",
        )

    logger.info(f"Uploading file: {file.filename} ({file_size} bytes)")

    try:
        result = await file_manager.upload_file_content(
            content=content,
            filename=file.filename,
        )

        return APIResponse(
            success=True,
            data=FileUploadResponse(
                file_id=result["file_id"],
                filename=result["filename"],
                size=result["size"],
                message="File uploaded successfully",
            ),
            message="文件上传成功",
        )

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}",
        )


@router.get(
    "",
    response_model=APIResponse[FileListResponse],
    summary="获取已上传文件列表",
    description="获取最近上传到 Manus 的文件列表",
)
async def list_files(
    file_manager: AsyncFileManager = Depends(get_file_manager),
):
    """获取已上传文件列表"""
    try:
        result = await file_manager.list_files()

        # 解析响应
        files_data = result.get("data", result.get("files", []))
        files = [
            FileResponse(
                id=f.get("id"),
                filename=f.get("filename", f.get("name", "unknown")),
                size=f.get("size"),
                created_at=f.get("created_at"),
            )
            for f in files_data
        ]

        return APIResponse(
            success=True,
            data=FileListResponse(
                files=files,
                total=len(files),
            ),
        )

    except Exception as e:
        logger.error(f"List files failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"List files failed: {str(e)}",
        )


@router.delete(
    "/{file_id}",
    response_model=APIResponse[FileDeleteResponse],
    summary="删除文件",
    description="从 Manus 删除已上传的文件",
)
async def delete_file(
    file_id: str,
    file_manager: AsyncFileManager = Depends(get_file_manager),
):
    """删除文件"""
    try:
        await file_manager.delete_file(file_id)

        return APIResponse(
            success=True,
            data=FileDeleteResponse(
                file_id=file_id,
                message="File deleted successfully",
            ),
            message="文件删除成功",
        )

    except Exception as e:
        logger.error(f"Delete file failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Delete file failed: {str(e)}",
        )

