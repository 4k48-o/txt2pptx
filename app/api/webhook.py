"""
Webhook API 端点

接收 Manus API 的 Webhook 回调，处理任务状态更新
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.websocket import manager
from app.dependencies import get_task_tracker, get_ppt_generator
from app.manus_client import AsyncManusClient
from app.services.video import VideoGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


# ========== Webhook Payload 模型 ==========

class TaskDetail(BaseModel):
    """任务详情（用于 task_created 和 task_stopped 事件）"""
    task_id: str
    task_title: Optional[str] = None
    task_url: Optional[str] = None
    message: Optional[str] = None
    status: Optional[str] = None
    attachments: Optional[list] = None
    stop_reason: Optional[str] = None  # finish, ask


class ProgressDetail(BaseModel):
    """进度详情（用于 task_progress 事件）"""
    task_id: str
    progress_type: Optional[str] = None  # plan_update
    message: Optional[str] = None


class ManusWebhookPayload(BaseModel):
    """Manus Webhook 回调数据结构（支持嵌套结构）"""
    event_id: str
    event_type: str  # task_created, task_progress, task_stopped
    
    # 嵌套结构（根据事件类型，可能包含其中一个）
    task_detail: Optional[TaskDetail] = None
    progress_detail: Optional[ProgressDetail] = None
    
    # 兼容扁平结构（向后兼容）
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    task_url: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    
    def get_task_id(self) -> str:
        """获取 task_id（优先从嵌套结构）"""
        if self.task_detail:
            return self.task_detail.task_id
        elif self.progress_detail:
            return self.progress_detail.task_id
        elif self.task_id:
            return self.task_id
        else:
            raise ValueError("无法找到 task_id")
    
    def get_task_title(self) -> Optional[str]:
        """获取 task_title"""
        if self.task_detail:
            return self.task_detail.task_title
        return self.task_title
    
    def get_task_url(self) -> Optional[str]:
        """获取 task_url"""
        if self.task_detail:
            return self.task_detail.task_url
        return self.task_url
    
    def get_status(self) -> Optional[str]:
        """获取 status"""
        if self.task_detail:
            return self.task_detail.status
        return self.status
    
    def get_message(self) -> Optional[str]:
        """获取 message"""
        if self.task_detail:
            return self.task_detail.message
        elif self.progress_detail:
            return self.progress_detail.message
        return self.message


# ========== Webhook 端点 ==========

@router.post("/manus")
async def manus_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    接收 Manus API 的 Webhook 回调
    
    Manus 要求：
    - 响应 HTTP 200 状态码
    - 10 秒内响应
    
    事件类型：
    - task_created: 任务创建成功
    - task_progress: 任务进度更新
    - task_stopped: 任务停止（完成或需要输入）
    """
    try:
        # 先读取原始请求体，用于调试
        raw_body = await request.body()
        logger.info(f"[Webhook] 收到原始请求体: {raw_body.decode('utf-8')[:500]}")
        
        # 尝试解析 JSON
        import json
        try:
            raw_data = json.loads(raw_body)
            logger.info(f"[Webhook] 解析后的 JSON 数据: {json.dumps(raw_data, ensure_ascii=False, indent=2)[:1000]}")
        except json.JSONDecodeError as e:
            logger.error(f"[Webhook] JSON 解析失败: {e}, 原始数据: {raw_body[:200]}")
            return {"status": "error", "message": "Invalid JSON"}, 400
        
        # 尝试解析为 Pydantic 模型
        try:
            payload = ManusWebhookPayload(**raw_data)
            logger.info(f"[Webhook] Pydantic 验证成功: event_type={payload.event_type}, task_id={payload.task_id}")
        except Exception as e:
            logger.error(f"[Webhook] Pydantic 验证失败: {e}")
            logger.error(f"[Webhook] 原始数据键: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'not dict'}")
            logger.error(f"[Webhook] 错误详情: {str(e)}")
            # 返回 200 避免 Manus 重试，但记录错误
            return {"status": "ok", "received": False, "error": "validation failed"}
        
        # 立即返回 200，在后台处理
        background_tasks.add_task(
            handle_webhook_event,
            payload
        )
        
        return {"status": "ok", "received": True}
        
    except Exception as e:
        logger.error(f"[Webhook] 处理请求异常: {e}", exc_info=True)
        # 即使出错也返回 200，避免 Manus 重试
        return {"status": "error", "message": str(e)}


async def handle_webhook_event(payload: ManusWebhookPayload):
    """
    后台处理 Webhook 事件
    """
    try:
        task_id = payload.get_task_id()
        logger.info(f"[Webhook] 开始处理事件: event_type={payload.event_type}, task_id={task_id}")
        
        tracker = get_task_tracker()
        
        # 记录 Webhook 事件到任务
        event = await tracker.add_webhook_event(
            task_id=task_id,
            event_id=payload.event_id,
            event_type=payload.event_type,
            status=payload.get_status(),
            message=payload.get_message(),
            raw_payload={
                "task_id": task_id,
                "task_title": payload.get_task_title(),
                "task_url": payload.get_task_url(),
                "status": payload.get_status(),
                "message": payload.get_message(),
            }
        )
        logger.info(f"[Webhook] 事件已记录: event_id={payload.event_id}")
        
        # 推送事件到所有订阅者
        await manager.send_to_task_subscribers(task_id, {
            "type": "webhook_event",
            "event_id": payload.event_id,
            "event_type": payload.event_type,
            "task_id": task_id,
            "status": payload.get_status(),
            "message": payload.get_message(),
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"[Webhook] 事件已推送给订阅者")
        
        # 根据事件类型处理
        if payload.event_type == "task_created":
            logger.info(f"[Webhook] 处理 task_created 事件")
            await handle_task_created(payload, tracker)
            
        elif payload.event_type == "task_progress":
            logger.info(f"[Webhook] 处理 task_progress 事件")
            await handle_task_progress(payload, tracker, task_id)
            
        elif payload.event_type == "task_stopped":
            logger.info(f"[Webhook] 处理 task_stopped 事件")
            await handle_task_stopped(payload, tracker)
            
        else:
            logger.warning(f"[Webhook] 未知的 Webhook 事件类型: {payload.event_type}")
            
    except Exception as e:
        logger.error(f"[Webhook] 处理 Webhook 事件失败: {e}", exc_info=True)


async def handle_task_created(payload: ManusWebhookPayload, tracker):
    """处理任务创建事件"""
    task_id = payload.get_task_id()
    task_title = payload.get_task_title()
    task_url = payload.get_task_url()
    
    logger.info(f"[Webhook] 任务已创建: task_id={task_id}, title={task_title}")
    
    # 更新本地任务状态
    local_task = await tracker.find_by_manus_task_id(task_id)
    if local_task:
        logger.info(f"[Webhook] 找到本地任务: {local_task['id']}, 更新状态")
        await tracker.update(
            local_task["id"],
            title=task_title,
            task_url=task_url,
            status="processing"
        )
    else:
        logger.warning(f"[Webhook] 未找到本地任务: task_id={task_id}")
    
    # 通过 WebSocket 通知前端
    await manager.send_to_task_subscribers(task_id, {
        "type": "task_created",
        "task_id": task_id,
        "title": task_title,
        "task_url": task_url,
        "message": "任务已创建，正在处理中...",
        "timestamp": datetime.now().isoformat()
    })


async def handle_task_progress(payload: ManusWebhookPayload, tracker, task_id: str):
    """处理任务进度事件"""
    message = payload.get_message()
    
    logger.info(f"[Webhook] 任务进度更新: task_id={task_id}, message={message}")
    
    # 检查是否是视频生成任务
    local_task = await tracker.find_by_manus_task_id(task_id)
    progress_type = "task_progress"  # 默认类型
    
    if local_task:
        task_data = await tracker.get(local_task["id"])
        if task_data:
            metadata = task_data.metadata or {}
            task_type = metadata.get("task_type")
            task_step = metadata.get("step")
            
            if task_type == "video_generation":
                # 根据步骤确定进度类型
                if task_step == "script_generation":
                    progress_type = "script_generation_progress"
                elif task_step == "video_generation":
                    progress_type = "video_generation_progress"
    
    # 通过 WebSocket 通知前端
    await manager.send_to_task_subscribers(task_id, {
        "type": progress_type,
        "task_id": task_id,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })


async def handle_task_stopped(payload: ManusWebhookPayload, tracker):
    """处理任务停止事件（完成或需要输入）"""
    task_id = payload.get_task_id()
    task_title = payload.get_task_title()
    status = payload.get_status()
    message = payload.get_message()
    stop_reason = payload.task_detail.stop_reason if payload.task_detail else None
    
    logger.info(f"[Webhook] 任务停止: task_id={task_id}, status={status}, stop_reason={stop_reason}")
    
    local_task = await tracker.find_by_manus_task_id(task_id)
    
    # 检查是否是视频生成任务
    is_video_task = False
    task_step = None
    if local_task:
        task_data = await tracker.get(local_task["id"])
        if task_data:
            metadata = task_data.metadata or {}
            task_type = metadata.get("task_type")
            task_step = metadata.get("step")
            is_video_task = task_type == "video_generation"
            logger.info(f"[Webhook] 任务类型: task_type={task_type}, step={task_step}, is_video_task={is_video_task}")
    
    if stop_reason == "finish":
        if is_video_task:
            # 视频生成任务完成处理
            await handle_video_task_stopped(
                payload, tracker, local_task, task_step, task_id
            )
        else:
            # PPT 生成任务完成 - 触发下载
            logger.info(f"[Webhook] PPT 任务完成，开始下载 PPTX: task_id={task_id}")
            
            if local_task:
                # 异步下载 PPTX
                try:
                    ppt_generator = await get_ppt_generator()
                    await ppt_generator.download_completed_task(task_id)
                    
                    # 重新获取更新后的任务信息
                    updated_task = await tracker.get(local_task["id"])
                    
                    await manager.send_to_task_subscribers(task_id, {
                        "type": "task_completed",
                        "task_id": task_id,
                        "local_task_id": local_task["id"],
                        "title": (updated_task.title if updated_task else None) or task_title,
                        "download_url": f"/api/tasks/{local_task['id']}/download",
                        "message": "PPT 生成完成！",
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.info(f"[Webhook] 任务完成通知已发送")
                except Exception as e:
                    logger.error(f"[Webhook] 下载 PPTX 失败: {e}", exc_info=True)
                    await manager.send_to_task_subscribers(task_id, {
                        "type": "task_failed",
                        "task_id": task_id,
                        "error": f"下载失败: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
            else:
                logger.warning(f"[Webhook] 任务完成但未找到本地任务: task_id={task_id}")
                await manager.send_to_task_subscribers(task_id, {
                    "type": "task_completed",
                    "task_id": task_id,
                    "title": task_title,
                    "message": "PPT 生成完成！",
                    "timestamp": datetime.now().isoformat()
                })
        
    elif stop_reason == "ask":
        # 需要用户输入
        logger.info(f"[Webhook] 任务需要用户输入: task_id={task_id}")
        
        if local_task:
            await tracker.update(
                local_task["id"],
                status="pending"
            )
        
        await manager.send_to_task_subscribers(task_id, {
            "type": "task_ask",
            "task_id": task_id,
            "message": message or "任务需要您的输入",
            "timestamp": datetime.now().isoformat()
        })
        
    else:
        # 其他情况（可能是失败）
        logger.warning(f"[Webhook] 未知的 stop_reason: {stop_reason}, task_id={task_id}")
        
        if local_task:
            await tracker.update(
                local_task["id"],
                status="failed",
                error=message or "任务执行失败"
            )
        
        await manager.send_to_task_subscribers(task_id, {
            "type": "task_failed",
            "task_id": task_id,
            "error": message or "任务执行失败",
            "timestamp": datetime.now().isoformat()
        })


async def handle_video_task_stopped(
    payload: ManusWebhookPayload,
    tracker,
    local_task: Optional[Dict[str, Any]],
    task_step: Optional[str],
    task_id: str,
):
    """
    处理视频生成任务停止事件
    
    Args:
        payload: Webhook 负载
        tracker: 任务追踪服务
        local_task: 本地任务信息
        task_step: 当前步骤（script_generation / video_generation）
        task_id: Manus 任务 ID
    """
    logger.info(f"[Webhook] 处理视频生成任务停止: task_id={task_id}, step={task_step}")
    
    if not local_task:
        logger.warning(f"[Webhook] 视频任务完成但未找到本地任务: task_id={task_id}")
        return
    
    local_task_id = local_task["id"]
    
    try:
        # 获取 Manus 客户端和视频生成服务
        from app.dependencies import get_manus_client
        async for client in get_manus_client():
            video_service = VideoGenerationService(client, tracker)
            
            if task_step == "script_generation":
                # 脚本生成完成，触发视频生成
                logger.info(f"[Webhook] 脚本生成完成，触发视频生成: local_task_id={local_task_id}, script_task_id={task_id}")
                
                try:
                    result = await video_service.handle_script_generation_complete(
                        local_task_id=local_task_id,
                        script_task_id=task_id,
                    )
                    
                    video_task_id = result.get("video_task_id")
                    
                    # 发送脚本生成完成通知
                    await manager.send_to_task_subscribers(task_id, {
                        "type": "script_generation_completed",
                        "task_id": task_id,
                        "local_task_id": local_task_id,
                        "video_task_id": video_task_id,
                        "message": "脚本生成完成，开始生成视频",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 同时订阅视频生成任务
                    if video_task_id:
                        await manager.send_to_task_subscribers(video_task_id, {
                            "type": "video_generation_started",
                            "task_id": video_task_id,
                            "local_task_id": local_task_id,
                            "message": "视频生成任务已创建",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    logger.info(f"[Webhook] 视频生成任务已创建: video_task_id={video_task_id}")
                    
                except Exception as e:
                    logger.error(f"[Webhook] 触发视频生成失败: {e}", exc_info=True)
                    await manager.send_to_task_subscribers(task_id, {
                        "type": "script_generation_failed",
                        "task_id": task_id,
                        "local_task_id": local_task_id,
                        "error": f"触发视频生成失败: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
                    # 更新任务状态为失败
                    await tracker.update(
                        local_task_id,
                        status="failed",
                        error=f"触发视频生成失败: {str(e)}"
                    )
            
            elif task_step == "video_generation":
                # 视频生成完成，下载视频
                logger.info(f"[Webhook] 视频生成完成，开始下载: local_task_id={local_task_id}, video_task_id={task_id}")
                
                try:
                    result = await video_service.handle_video_generation_complete(
                        local_task_id=local_task_id,
                        video_task_id=task_id,
                    )
                    
                    video_path = result.get("video_path")
                    
                    # 更新任务状态为完成
                    await tracker.update(
                        local_task_id,
                        status="completed"
                    )
                    
                    # 发送视频生成完成通知
                    await manager.send_to_task_subscribers(task_id, {
                        "type": "video_generation_completed",
                        "task_id": task_id,
                        "local_task_id": local_task_id,
                        "video_path": video_path,
                        "download_url": f"/api/v1/video/tasks/{local_task_id}/download",
                        "message": "视频生成完成！",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    logger.info(f"[Webhook] 视频生成完成通知已发送: video_path={video_path}")
                    
                except Exception as e:
                    logger.error(f"[Webhook] 下载视频失败: {e}", exc_info=True)
                    await manager.send_to_task_subscribers(task_id, {
                        "type": "video_generation_failed",
                        "task_id": task_id,
                        "local_task_id": local_task_id,
                        "error": f"下载视频失败: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
                    # 更新任务状态为失败
                    await tracker.update(
                        local_task_id,
                        status="failed",
                        error=f"下载视频失败: {str(e)}"
                    )
            else:
                logger.warning(f"[Webhook] 未知的视频任务步骤: step={task_step}, task_id={task_id}")
            
            break  # 只使用第一个客户端实例
            
    except Exception as e:
        logger.error(f"[Webhook] 处理视频任务停止失败: {e}", exc_info=True)
        await manager.send_to_task_subscribers(task_id, {
            "type": "task_failed",
            "task_id": task_id,
            "local_task_id": local_task_id,
            "error": f"处理失败: {str(e)}",
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
        webhook_url = settings.webhook_callback_url()
    
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

