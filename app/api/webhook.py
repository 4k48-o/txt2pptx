"""
Webhook API 端点

接收 Manus API 的 Webhook 回调，处理任务状态更新
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.websocket import manager
from app.dependencies import get_task_tracker, get_ppt_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


# ========== Webhook Payload 模型 ==========

class ManusWebhookPayload(BaseModel):
    """Manus Webhook 回调数据结构"""
    event_id: str
    event_type: str  # task_created, task_state_change
    task_id: str
    task_title: Optional[str] = None
    task_url: Optional[str] = None
    status: Optional[str] = None  # pending, running, completed, failed
    message: Optional[str] = None


# ========== Webhook 端点 ==========

@router.post("/manus")
async def manus_webhook(
    request: Request,
    payload: ManusWebhookPayload,
    background_tasks: BackgroundTasks
):
    """
    接收 Manus API 的 Webhook 回调
    
    Manus 要求：
    - 响应 HTTP 200 状态码
    - 10 秒内响应
    
    事件类型：
    - task_created: 任务创建成功
    - task_state_change: 任务状态变化（running/completed/failed）
    """
    logger.info(f"收到 Manus Webhook: event_type={payload.event_type}, task_id={payload.task_id}")
    
    # 立即返回 200，在后台处理
    background_tasks.add_task(
        handle_webhook_event,
        payload
    )
    
    return {"status": "ok", "received": True}


async def handle_webhook_event(payload: ManusWebhookPayload):
    """
    后台处理 Webhook 事件
    """
    try:
        tracker = get_task_tracker()
        
        # 记录 Webhook 事件到任务
        event = await tracker.add_webhook_event(
            task_id=payload.task_id,
            event_id=payload.event_id,
            event_type=payload.event_type,
            status=payload.status,
            message=payload.message,
            raw_payload={
                "task_id": payload.task_id,
                "task_title": payload.task_title,
                "task_url": payload.task_url,
                "status": payload.status,
                "message": payload.message,
            }
        )
        
        # 推送事件到所有订阅者
        await manager.send_to_task_subscribers(payload.task_id, {
            "type": "webhook_event",
            "event_id": payload.event_id,
            "event_type": payload.event_type,
            "task_id": payload.task_id,
            "status": payload.status,
            "message": payload.message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 根据事件类型处理
        if payload.event_type == "task_created":
            await handle_task_created(payload, tracker)
            
        elif payload.event_type == "task_state_change":
            await handle_task_state_change(payload, tracker)
            
        else:
            logger.warning(f"未知的 Webhook 事件类型: {payload.event_type}")
            
    except Exception as e:
        logger.error(f"处理 Webhook 事件失败: {e}")


async def handle_task_created(payload: ManusWebhookPayload, tracker):
    """处理任务创建事件"""
    logger.info(f"任务已创建: task_id={payload.task_id}, title={payload.task_title}")
    
    # 更新本地任务状态
    local_task = await tracker.find_by_manus_task_id(payload.task_id)
    if local_task:
        await tracker.update(
            local_task["id"],
            title=payload.task_title,
            task_url=payload.task_url,
            status="processing"
        )
    
    # 通过 WebSocket 通知前端
    await manager.send_to_task_subscribers(payload.task_id, {
        "type": "task_created",
        "task_id": payload.task_id,
        "title": payload.task_title,
        "task_url": payload.task_url,
        "message": "任务已创建，正在处理中...",
        "timestamp": datetime.now().isoformat()
    })


async def handle_task_state_change(payload: ManusWebhookPayload, tracker):
    """处理任务状态变化事件"""
    logger.info(f"任务状态变化: task_id={payload.task_id}, status={payload.status}")
    
    local_task = await tracker.find_by_manus_task_id(payload.task_id)
    
    if payload.status == "running":
        # 任务运行中
        if local_task:
            await tracker.update(local_task["id"], status="processing")
        
        await manager.send_to_task_subscribers(payload.task_id, {
            "type": "task_update",
            "task_id": payload.task_id,
            "status": "running",
            "message": "PPT 正在生成中...",
            "timestamp": datetime.now().isoformat()
        })
        
    elif payload.status == "completed":
        # 任务完成 - 触发下载
        logger.info(f"任务完成，开始下载 PPTX: task_id={payload.task_id}")
        
        if local_task:
            # 异步下载 PPTX
            try:
                ppt_generator = await get_ppt_generator()
                await ppt_generator.download_completed_task(payload.task_id)
                
                # 重新获取更新后的任务信息
                updated_task = await tracker.get(local_task["id"])
                
                await manager.send_to_task_subscribers(payload.task_id, {
                    "type": "task_completed",
                    "task_id": payload.task_id,
                    "local_task_id": local_task["id"],
                    "title": (updated_task.title if updated_task else None) or payload.task_title,
                    "download_url": f"/api/tasks/{local_task['id']}/download",
                    "message": "PPT 生成完成！",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"下载 PPTX 失败: {e}")
                await manager.send_to_task_subscribers(payload.task_id, {
                    "type": "task_failed",
                    "task_id": payload.task_id,
                    "error": f"下载失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        else:
            await manager.send_to_task_subscribers(payload.task_id, {
                "type": "task_completed",
                "task_id": payload.task_id,
                "title": payload.task_title,
                "message": "PPT 生成完成！",
                "timestamp": datetime.now().isoformat()
            })
        
    elif payload.status == "failed":
        # 任务失败
        if local_task:
            await tracker.update(
                local_task["id"],
                status="failed",
                error=payload.message or "任务执行失败"
            )
        
        await manager.send_to_task_subscribers(payload.task_id, {
            "type": "task_failed",
            "task_id": payload.task_id,
            "error": payload.message or "任务执行失败",
            "timestamp": datetime.now().isoformat()
        })


# ========== 辅助端点 ==========

@router.get("/status")
async def webhook_status():
    """检查 Webhook 端点状态"""
    from app.config import get_settings
    settings = get_settings()
    
    webhook_url = ""
    if settings.webhook_base_url:
        webhook_url = f"{settings.webhook_base_url.rstrip('/')}{settings.webhook_path}"
    
    return {
        "enabled": settings.webhook_enabled,
        "webhook_url": webhook_url,
        "path": settings.webhook_path,
        "message": "Webhook 端点就绪" if settings.webhook_enabled else "Webhook 未启用"
    }


@router.get("/events/{task_id}")
async def get_task_webhook_events(task_id: str):
    """
    获取任务的所有 Webhook 事件列表
    
    Args:
        task_id: 任务 ID（本地或 Manus）
    """
    tracker = get_task_tracker()
    events = await tracker.get_webhook_events(task_id)
    
    return {
        "success": True,
        "task_id": task_id,
        "events": events,
        "count": len(events),
        "timestamp": datetime.now().isoformat()
    }

