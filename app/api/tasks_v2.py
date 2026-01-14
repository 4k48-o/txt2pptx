"""
Tasks V2 API - Webhook 模式任务管理

与 v1 的区别：
- 不使用后台轮询
- 通过 Webhook 接收 Manus 回调
- 通过 WebSocket 推送状态给前端
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    LocalTaskStatus,
    APIResponse,
)
from ..services import TaskTrackerService, PPTGeneratorService
from ..dependencies import get_task_tracker, get_ppt_generator
from ..websocket import manager
from ..manus_client import AsyncManusClient, AsyncTaskManager
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/tasks", tags=["tasks-v2"])


class CreateTaskV2Request(CreateTaskRequest):
    """V2 创建任务请求，增加 client_id"""
    client_id: Optional[str] = None  # WebSocket 客户端 ID，用于推送更新


@router.post(
    "",
    response_model=APIResponse[CreateTaskResponse],
    summary="创建 PPT 生成任务 (Webhook 模式)",
    description="创建任务后通过 Webhook 回调更新状态，通过 WebSocket 推送给前端",
)
async def create_task_v2(
    request: CreateTaskV2Request,
    tracker: TaskTrackerService = Depends(get_task_tracker),
):
    """
    创建 PPT 生成任务 (Webhook 模式)

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
            detail="Webhook 模式未启用，请使用 /api/tasks 轮询模式，或配置 WEBHOOK_ENABLED=true"
        )
    
    logger.info(f"[V2] Creating task with prompt: {request.prompt[:50]}...")
    
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
        
        logger.info(f"[V2] Task created: local_id={local_task.id}, manus_id={manus_task_id}")
        
        await client.close()
        
        return APIResponse(
            success=True,
            data=CreateTaskResponse(
                id=local_task.id,
                status=LocalTaskStatus.PROCESSING,
                message="Task created, waiting for Manus webhook callback",
            ),
            message="任务创建成功，等待 Manus 处理",
        )
        
    except Exception as e:
        logger.error(f"[V2] Failed to create Manus task: {e}")
        
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
        webhook_url = f"{settings.webhook_base_url.rstrip('/')}{settings.webhook_path}"
    
    return APIResponse(
        success=True,
        data={
            "webhook_enabled": settings.webhook_enabled,
            "webhook_url": webhook_url,
            "websocket_connections": manager.active_count,
            "message": "Webhook 模式已启用" if settings.webhook_enabled else "Webhook 模式未启用",
        }
    )
