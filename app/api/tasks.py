"""
Tasks API - 任务管理路由
"""

import logging
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskResponse,
    TaskListResponse,
    TaskListItem,
    TaskProgressResponse,
    LocalTaskStatus,
    APIResponse,
)
from ..services import TaskTrackerService, PPTGeneratorService
from ..dependencies import get_task_tracker, get_ppt_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=APIResponse[CreateTaskResponse],
    summary="创建 PPT 生成任务",
    description="创建新的 PPT 生成任务，立即返回任务 ID，后台异步执行生成流程",
)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    generator: PPTGeneratorService = Depends(get_ppt_generator),
):
    """
    创建 PPT 生成任务

    - 接收 prompt 和可选的 attachments
    - 立即返回本地 task_id
    - 后台异步执行任务
    """
    logger.info(f"Creating task with prompt: {request.prompt[:50]}...")

    # 创建本地任务记录
    attachments = None
    if request.attachments:
        attachments = [
            {"filename": a.filename, "file_id": a.file_id}
            for a in request.attachments
        ]

    local_task = await tracker.create(
        prompt=request.prompt,
        attachments=attachments,
    )

    # 添加后台任务
    background_tasks.add_task(
        generator.generate_ppt,
        local_task.id,
    )

    logger.info(f"Task created: {local_task.id}, background task started")

    return APIResponse(
        success=True,
        data=CreateTaskResponse(
            id=local_task.id,
            status=LocalTaskStatus.PENDING,
            message="Task created, processing in background",
        ),
        message="任务创建成功，后台处理中",
    )


@router.get(
    "",
    response_model=APIResponse[TaskListResponse],
    summary="获取任务列表",
    description="获取所有任务列表，支持分页和状态过滤",
)
async def list_tasks(
    status: Optional[str] = Query(
        None,
        description="状态过滤: pending, uploading, processing, downloading, completed, failed",
    ),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """获取任务列表"""
    tasks = await tracker.list(status=status, limit=limit, offset=offset)
    total = await tracker.count(status=status)

    task_items = [
        TaskListItem(
            id=t.id,
            status=LocalTaskStatus(t.status),
            prompt=t.prompt,
            credit_usage=t.credit_usage,
            metadata={"task_title": t.title, "task_url": t.task_url} if t.title else None,
            created_at=t.created_at,
        )
        for t in tasks
    ]

    return APIResponse(
        success=True,
        data=TaskListResponse(
            tasks=task_items,
            total=total,
            has_more=(offset + limit) < total,
        ),
    )


@router.get(
    "/{task_id}",
    response_model=APIResponse[TaskProgressResponse],
    summary="获取任务详情",
    description="获取指定任务的详细信息和进度",
)
async def get_task(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """获取任务详情"""
    task = await tracker.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return APIResponse(
        success=True,
        data=TaskProgressResponse(
            task_id=task.id,
            status=LocalTaskStatus(task.status),
            title=task.title,
            task_url=task.task_url,
            message_count=0,  # 本地不跟踪消息数
            credit_usage=task.credit_usage,
        ),
    )


@router.get(
    "/{task_id}/detail",
    summary="获取任务完整详情",
    description="获取任务的所有信息，包括下载链接",
)
async def get_task_detail(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """获取任务完整详情"""
    task = await tracker.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return APIResponse(
        success=True,
        data={
            "id": task.id,
            "manus_task_id": task.manus_task_id,
            "status": task.status,
            "prompt": task.prompt,
            "title": task.title,
            "task_url": task.task_url,
            "pptx_url": task.pptx_url,
            "pptx_filename": task.pptx_filename,
            "local_file_path": task.local_file_path,
            "credit_usage": task.credit_usage,
            "error": task.error,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        },
    )


@router.get(
    "/{task_id}/download",
    summary="下载 PPT 文件",
    description="下载已完成任务的 PPT 文件",
)
async def download_task_file(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """下载 PPT 文件"""
    task = await tracker.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task.status != LocalTaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed yet, current status: {task.status}",
        )

    if not task.local_file_path:
        raise HTTPException(
            status_code=404,
            detail="PPT file not found, please check task status",
        )

    file_path = Path(task.local_file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {task.local_file_path}",
        )

    filename = task.pptx_filename or f"ppt_{task_id[:8]}.pptx"
    # 确保文件名有 .pptx 后缀
    if not filename.lower().endswith('.pptx'):
        filename = f"{filename}.pptx"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.delete(
    "/{task_id}",
    response_model=APIResponse,
    summary="删除任务",
    description="删除指定任务及其相关文件",
)
async def delete_task(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """删除任务"""
    task = await tracker.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # 删除本地文件
    if task.local_file_path:
        file_path = Path(task.local_file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")

    # 删除任务记录
    await tracker.delete(task_id)

    return APIResponse(
        success=True,
        message=f"Task {task_id} deleted successfully",
    )

