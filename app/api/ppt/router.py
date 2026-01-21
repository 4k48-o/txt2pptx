"""
PPT Service Router - PPT 生成服务路由

整合轮询模式和 Webhook 模式的任务管理
"""

import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ...schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskResponse,
    TaskListResponse,
    TaskListItem,
    TaskProgressResponse,
    TaskDetailResponse,
    LocalTaskStatus,
    TaskStatus,
    APIResponse,
)
from ...services import TaskTrackerService, PPTGeneratorService
from ...dependencies import get_task_tracker, get_ppt_generator, get_manus_client
from ...manus_client import AsyncManusClient, AsyncTaskManager
from ...websocket import manager
from ...config import get_settings
from ...exceptions import ManusAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ppt/tasks", tags=["ppt"])


# ========== 轮询模式 API ==========

@router.post(
    "",
    response_model=APIResponse[CreateTaskResponse],
    summary="创建 PPT 生成任务（轮询模式）",
    description="创建新的 PPT 生成任务，立即返回任务 ID，后台异步执行生成流程",
)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    generator: PPTGeneratorService = Depends(get_ppt_generator),
):
    """
    创建 PPT 生成任务（轮询模式）

    - 接收 prompt 和可选的 attachments
    - 立即返回本地 task_id
    - 后台异步执行任务
    """
    logger.info(f"Creating PPT task with prompt: {request.prompt[:50]}...")

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

    logger.info(f"PPT task created: {local_task.id}, background task started")

    return APIResponse(
        success=True,
        data=CreateTaskResponse(
            id=local_task.id,
            status=TaskStatus.PENDING,
            message="Task created, processing in background",
        ),
        message="任务创建成功，后台处理中",
    )


# ========== Webhook 模式 API ==========

class CreateTaskV2Request(CreateTaskRequest):
    """Webhook 模式创建任务请求，增加 client_id"""
    client_id: Optional[str] = None  # WebSocket 客户端 ID，用于推送更新


@router.post(
    "/webhook",
    response_model=APIResponse[CreateTaskResponse],
    summary="创建 PPT 生成任务（Webhook 模式）",
    description="创建任务后通过 Webhook 回调更新状态，通过 WebSocket 推送给前端",
)
async def create_task_webhook(
    request: CreateTaskV2Request,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """
    创建 PPT 生成任务（Webhook 模式）

    流程：
    1. 创建本地任务记录
    2. 调用 Manus API 创建任务
    3. 如果提供了 client_id，自动订阅任务更新
    4. 等待 Manus Webhook 回调
    5. 通过 WebSocket 推送状态给前端
    """
    settings = get_settings()
    
    # 检查 Webhook 是否启用
    if not settings.webhook_enabled:
        raise HTTPException(
            status_code=400,
            detail="Webhook 模式未启用，请使用 /api/ppt/tasks 轮询模式，或配置 WEBHOOK_ENABLED=true"
        )
    
    logger.info(f"[Webhook] Creating PPT task with prompt: {request.prompt[:50]}...")
    
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
    
    # 更新状态为处理中
    await tracker.update(local_task.id, status=LocalTaskStatus.PROCESSING.value)
    
    # 如果提供了 client_id，自动订阅任务更新
    if request.client_id and manager.is_connected(request.client_id):
        # 先订阅本地任务 ID（前端用这个查询）
        await manager.subscribe_task(request.client_id, local_task.id)
    
    try:
        # 调用 Manus API 创建任务
        client = AsyncManusClient()
        task_manager = AsyncTaskManager(client)
        
        manus_result = await task_manager.create_task(
            prompt=request.prompt,
            attachments=attachments,
        )
        
        manus_task_id = manus_result.get("task_id")
        
        # 更新本地任务，关联 Manus 任务 ID
        await tracker.update(
            local_task.id,
            manus_task_id=manus_task_id,
        )
        
        # 订阅 Manus 任务 ID 的更新（Webhook 用这个推送）
        if request.client_id and manager.is_connected(request.client_id):
            await manager.subscribe_task(request.client_id, manus_task_id)
        
        logger.info(f"[Webhook] PPT task created: local_id={local_task.id}, manus_id={manus_task_id}")
        
        await client.close()
        
        return APIResponse(
            success=True,
            data=CreateTaskResponse(
                id=local_task.id,
                status=TaskStatus.RUNNING,
                message="Task created, waiting for Manus webhook callback",
            ),
            message="任务创建成功，等待 Manus 处理",
        )
        
    except Exception as e:
        # 打印更详细的错误信息（包括 Manus API 的 detail）
        if isinstance(e, ManusAPIException):
            logger.error(
                "[Webhook] ManusAPIException when creating PPT task: %s, detail=%s",
                e.message,
                e.detail,
            )
        else:
            logger.error(f"[Webhook] Failed to create Manus PPT task: {e}")
        
        # 更新本地任务状态为失败
        await tracker.update(
            local_task.id,
            status=LocalTaskStatus.FAILED.value,
            error=str(e),
        )
        
        # 通过 WebSocket 通知失败
        if request.client_id:
            await manager.send_to_client(request.client_id, {
                "type": "task_failed",
                "task_id": local_task.id,
                "error": str(e),
            })
        
        raise HTTPException(
            status_code=500,
            detail=f"创建 Manus 任务失败: {str(e)}"
        )


@router.get("/webhook-status")
async def get_webhook_status():
    """获取 Webhook 模式状态"""
    settings = get_settings()
    
    webhook_url = ""
    if settings.webhook_base_url:
        webhook_url = settings.webhook_callback_url()
    
    return APIResponse(
        success=True,
        data={
            "webhook_enabled": settings.webhook_enabled,
            "webhook_url": webhook_url,
            "websocket_connections": manager.active_count,
            "message": "Webhook 模式已启用" if settings.webhook_enabled else "Webhook 模式未启用",
        }
    )


# ========== 通用任务管理 API ==========

@router.get(
    "",
    response_model=APIResponse[TaskListResponse],
    summary="获取 PPT 任务列表",
    description="获取所有 PPT 任务列表，支持分页和状态过滤",
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
    """获取 PPT 任务列表"""
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
    summary="获取 PPT 任务详情",
    description="获取指定 PPT 任务的详细信息和进度",
)
async def get_task(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """获取 PPT 任务详情"""
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
            message_count=0,
            credit_usage=task.credit_usage,
        ),
    )


@router.get(
    "/{task_id}/detail",
    summary="获取 PPT 任务完整详情",
    description="获取 PPT 任务的所有信息，包括下载链接",
)
async def get_task_detail(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """获取 PPT 任务完整详情"""
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
    "/manus/{manus_task_id}",
    response_model=APIResponse,
    summary="通过 Manus 任务 ID 查询 PPT 任务详情",
    description="直接通过 Manus 任务 ID 从 Manus API 查询任务详情（无需本地任务记录）",
)
async def get_task_by_manus_id(
    manus_task_id: str,
    client: AsyncManusClient = Depends(get_manus_client),
):
    """通过 Manus 任务 ID 查询 PPT 任务详情"""
    try:
        task_manager = AsyncTaskManager(client)
        task_result = await task_manager.get_task(manus_task_id, convert=True)
        
        return APIResponse(
            success=True,
            data=task_result,
            message="任务查询成功",
        )
    except Exception as e:
        logger.error(f"查询 Manus PPT 任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询任务失败: {str(e)}",
        )


@router.get(
    "/{task_id}/full",
    response_model=APIResponse,
    summary="获取 PPT 任务完整详情（含所有文件）",
    description="从 Manus API 获取任务的完整信息，包括所有生成的文件",
)
async def get_task_full_detail(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    client: AsyncManusClient = Depends(get_manus_client),
):
    """获取 PPT 任务完整详情，包括从 Manus API 获取的所有文件"""
    from ...schemas import TaskDetailResponse, TaskFile
    
    # 获取本地任务
    local_task = await tracker.get(task_id)
    if not local_task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # 如果没有 Manus 任务 ID，只返回本地信息
    if not local_task.manus_task_id:
        return APIResponse(
            success=True,
            data=TaskDetailResponse(
                id=local_task.id,
                status=TaskStatus(local_task.status) if local_task.status in ["pending", "running", "completed", "failed"] else TaskStatus.PENDING,
                prompt=local_task.prompt,
                title=local_task.title,
                task_url=local_task.task_url,
                credit_usage=local_task.credit_usage,
                created_at=datetime.fromisoformat(local_task.created_at) if local_task.created_at else None,
                updated_at=datetime.fromisoformat(local_task.updated_at) if local_task.updated_at else None,
                local_file_path=local_task.local_file_path,
            ),
        )

    # 从 Manus API 获取完整任务信息
    try:
        task_manager = AsyncTaskManager(client)
        manus_task = await task_manager.get_task(local_task.manus_task_id, convert=True)
        
        # 提取所有文件
        files = []
        output_messages = manus_task.get("output", [])
        
        logger.info(f"提取 PPT 任务文件: task_id={local_task.manus_task_id}, output_messages_count={len(output_messages)}")
        
        for message in output_messages:
            message_type = message.get("type")
            if message_type == "message":
                content_items = message.get("content", [])
                for content in content_items:
                    content_type = content.get("type")
                    if content_type == "output_file":
                        file_url = content.get("fileUrl") or content.get("file_url")
                        file_name = content.get("fileName") or content.get("file_name")
                        mime_type = content.get("mimeType") or content.get("mime_type")
                        
                        if file_url and file_name:
                            files.append(TaskFile(
                                fileUrl=file_url,
                                fileName=file_name,
                                mimeType=mime_type,
                            ))
                            logger.debug(f"找到文件: {file_name} ({mime_type})")
        
        logger.info(f"提取到 {len(files)} 个文件")
        
        # 构建响应
        return APIResponse(
            success=True,
            data=TaskDetailResponse(
                id=local_task.id,
                status=TaskStatus(manus_task.get("status", local_task.status)),
                prompt=local_task.prompt,
                title=manus_task.get("metadata", {}).get("task_title") or local_task.title,
                task_url=manus_task.get("metadata", {}).get("task_url") or local_task.task_url,
                credit_usage=manus_task.get("credit_usage") or local_task.credit_usage,
                created_at=datetime.fromtimestamp(manus_task.get("created_at", 0)) if manus_task.get("created_at") else (datetime.fromisoformat(local_task.created_at) if local_task.created_at else None),
                updated_at=datetime.fromtimestamp(manus_task.get("updated_at", 0)) if manus_task.get("updated_at") else (datetime.fromisoformat(local_task.updated_at) if local_task.updated_at else None),
                files=files,
                output=output_messages,
                local_file_path=local_task.local_file_path,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to get PPT task detail from Manus API: {e}")
        # 如果 Manus API 调用失败，返回本地信息
        return APIResponse(
            success=True,
            data=TaskDetailResponse(
                id=local_task.id,
                status=TaskStatus(local_task.status) if local_task.status in ["pending", "running", "completed", "failed"] else TaskStatus.PENDING,
                prompt=local_task.prompt,
                title=local_task.title,
                task_url=local_task.task_url,
                credit_usage=local_task.credit_usage,
                created_at=datetime.fromisoformat(local_task.created_at) if local_task.created_at else None,
                updated_at=datetime.fromisoformat(local_task.updated_at) if local_task.updated_at else None,
                local_file_path=local_task.local_file_path,
            ),
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
    summary="删除 PPT 任务",
    description="删除指定 PPT 任务及其相关文件",
)
async def delete_task(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """删除 PPT 任务"""
    task = await tracker.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # 删除本地文件
    if task.local_file_path:
        file_path = Path(task.local_file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted PPT file: {file_path}")

    # 删除任务记录
    await tracker.delete(task_id)

    return APIResponse(
        success=True,
        message=f"PPT task {task_id} deleted successfully",
    )
