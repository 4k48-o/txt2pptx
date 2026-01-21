"""
测试 API 路由 - 历史数据回放
用于模拟视频生成流程，基于 tasks.json 中的历史数据
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ...config import get_settings
from ...dependencies import get_task_tracker
from ...services import TaskTrackerService
from ...websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["test"])


class ReplayRequest(BaseModel):
    """回放请求"""
    task_id: str = Field(..., description="tasks.json 中的任务 ID")
    client_id: Optional[str] = Field(None, description="WebSocket 客户端 ID（可选）")
    speed: float = Field(1.0, ge=0.1, le=10.0, description="回放速度倍数（1.0 = 正常速度，2.0 = 2倍速）")
    local_task_id: Optional[str] = Field(None, description="本地任务 ID（如果已存在）")


class ReplayResponse(BaseModel):
    """回放响应"""
    success: bool
    message: str
    local_task_id: str
    script_task_id: str
    video_task_id: str
    total_events: int
    estimated_duration: float


def load_tasks_json(settings=None) -> Dict[str, Any]:
    """加载 tasks.json 文件"""
    if settings is None:
        settings = get_settings()
    
    # 尝试多个可能的路径（按优先级）
    possible_paths = []
    
    # 1. 使用配置的 output_dir
    if hasattr(settings, 'output_dir'):
        output_dir = Path(settings.output_dir)
        if output_dir.is_absolute():
            possible_paths.append(output_dir / "tasks.json")
        else:
            # 相对路径，需要从项目根目录解析
            project_root = Path(__file__).parent.parent.parent.parent
            possible_paths.append(project_root / output_dir / "tasks.json")
    
    # 2. 使用配置的 tasks_file
    if hasattr(settings, 'tasks_file'):
        tasks_file_path = Path(settings.tasks_file)
        if tasks_file_path.is_absolute():
            possible_paths.append(tasks_file_path)
        else:
            project_root = Path(__file__).parent.parent.parent.parent
            possible_paths.append(project_root / tasks_file_path)
    
    # 3. 默认路径：项目根目录下的 output/tasks.json
    project_root = Path(__file__).parent.parent.parent.parent
    possible_paths.append(project_root / "output" / "tasks.json")
    
    # 4. 当前工作目录下的 output/tasks.json
    possible_paths.append(Path("output") / "tasks.json")
    possible_paths.append(Path("./output/tasks.json"))
    
    # 查找存在的文件
    tasks_file = None
    for path in possible_paths:
        try:
            abs_path = path.resolve() if not path.is_absolute() else path
            if abs_path.exists() and abs_path.is_file():
                tasks_file = abs_path
                logger.debug(f"找到 tasks.json: {tasks_file}")
                break
        except Exception as e:
            logger.debug(f"检查路径失败 {path}: {e}")
            continue
    
    if tasks_file is None:
        error_msg = f"tasks.json 文件不存在。尝试过的路径: {[str(p) for p in possible_paths]}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg
        )
    
    try:
        with open(tasks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"成功加载 tasks.json: {tasks_file}, 任务数: {len(data)}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"tasks.json JSON 解析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"tasks.json JSON 格式错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"加载 tasks.json 失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载 tasks.json 失败: {str(e)}"
        )


def parse_webhook_events(task_data: Dict[str, Any]) -> tuple[str, str, List[Dict[str, Any]]]:
    """
    解析任务的 webhook_events，提取 script_task_id 和 video_task_id
    
    Returns:
        (script_task_id, video_task_id, sorted_events)
    """
    metadata = task_data.get("metadata", {})
    script_task_id = metadata.get("script_task_id")
    video_task_id = metadata.get("video_task_id")
    
    webhook_events = task_data.get("webhook_events", [])
    
    # 如果没有在 metadata 中找到，尝试从 webhook_events 中提取
    if not script_task_id or not video_task_id:
        for event in webhook_events:
            raw_payload = event.get("raw_payload", {})
            task_id = raw_payload.get("task_id")
            event_type = event.get("event_type")
            
            # 第一个 task_created 通常是 script_task_id
            if event_type == "task_created" and not script_task_id:
                script_task_id = task_id
            
            # 第二个 task_created 通常是 video_task_id
            elif event_type == "task_created" and script_task_id and task_id != script_task_id:
                video_task_id = task_id
    
    # 按时间戳排序事件
    sorted_events = sorted(
        webhook_events,
        key=lambda x: datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00"))
    )
    
    return script_task_id, video_task_id, sorted_events


def convert_webhook_to_websocket_message(
    event: Dict[str, Any],
    script_task_id: str,
    video_task_id: str,
    local_task_id: str,
) -> Optional[Dict[str, Any]]:
    """
    将 webhook 事件转换为 WebSocket 消息
    
    Returns:
        WebSocket 消息字典，如果不需要发送则返回 None
    """
    event_type = event.get("event_type")
    raw_payload = event.get("raw_payload", {})
    task_id = raw_payload.get("task_id")
    message = event.get("message") or raw_payload.get("message")
    timestamp = event.get("timestamp")
    
    # 判断是脚本生成任务还是视频生成任务
    is_script_task = task_id == script_task_id
    is_video_task = task_id == video_task_id
    
    if event_type == "task_created":
        # task_created 事件通常不需要发送给前端
        # 但如果是视频生成任务的创建，可以发送 video_generation_started
        if is_video_task:
            return {
                "type": "video_generation_started",
                "task_id": video_task_id,
                "local_task_id": local_task_id,
                "message": "视频生成任务已创建",
                "timestamp": timestamp or datetime.now().isoformat()
            }
        return None
    
    elif event_type == "task_progress":
        if is_script_task:
            return {
                "type": "script_generation_progress",
                "task_id": script_task_id,
                "local_task_id": local_task_id,
                "message": message or "Processing...",
                "timestamp": timestamp or datetime.now().isoformat()
            }
        elif is_video_task:
            return {
                "type": "video_generation_progress",
                "task_id": video_task_id,
                "local_task_id": local_task_id,
                "message": message or "Processing...",
                "timestamp": timestamp or datetime.now().isoformat()
            }
        return None
    
    elif event_type == "task_stopped":
        # 检查 stop_reason（如果有的话）
        # 这里假设 finish 表示成功完成
        if is_script_task:
            return {
                "type": "script_generation_completed",
                "task_id": script_task_id,
                "local_task_id": local_task_id,
                "video_task_id": video_task_id,
                "message": "脚本生成完成，开始生成视频",
                "timestamp": timestamp or datetime.now().isoformat()
            }
        elif is_video_task:
            # 构建下载 URL
            download_url = f"/api/video/tasks/{local_task_id}/download"
            
            return {
                "type": "video_generation_completed",
                "task_id": video_task_id,
                "local_task_id": local_task_id,
                "download_url": download_url,
                "message": "视频生成完成！",
                "timestamp": timestamp or datetime.now().isoformat()
            }
        return None
    
    return None


async def replay_webhook_events(
    local_task_id: str,
    script_task_id: str,
    video_task_id: str,
    events: List[Dict[str, Any]],
    speed: float = 1.0,
):
    """
    回放 webhook 事件，通过 WebSocket 发送消息
    
    Args:
        local_task_id: 本地任务 ID
        script_task_id: 脚本生成任务 ID
        video_task_id: 视频生成任务 ID
        events: webhook 事件列表（已按时间排序）
        speed: 回放速度倍数
    """
    if not events:
        logger.warning("没有事件需要回放")
        return
    
    # 记录开始时间
    start_time = datetime.now()
    first_event_time = datetime.fromisoformat(events[0]["timestamp"].replace("Z", "+00:00"))
    
    # 订阅任务（确保消息能发送到前端）
    # 注意：这里假设前端已经订阅了 local_task_id
    # 我们还需要订阅 script_task_id 和 video_task_id
    
    logger.info(f"开始回放任务: local_task_id={local_task_id}, 事件数={len(events)}, 速度={speed}x")
    
    for i, event in enumerate(events):
        # 计算延迟
        if i > 0:
            current_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            prev_time = datetime.fromisoformat(events[i-1]["timestamp"].replace("Z", "+00:00"))
            delay_seconds = (current_time - prev_time).total_seconds()
            
            # 应用速度倍数
            actual_delay = delay_seconds / speed
            
            # 限制延迟范围：最小 0.3 秒，最大 5 秒（避免等待时间过长）
            if actual_delay > 0:
                delay = max(0.3, min(actual_delay, 5.0))
                await asyncio.sleep(delay)
        
        # 转换为 WebSocket 消息
        ws_message = convert_webhook_to_websocket_message(
            event, script_task_id, video_task_id, local_task_id
        )
        
        if ws_message:
            # 获取任务 ID（用于发送消息）
            task_id = ws_message.get("task_id")
            
            # 发送消息给订阅者
            if task_id:
                await manager.send_to_task_subscribers(task_id, ws_message)
            
            # 同时发送给 local_task_id 的订阅者
            await manager.send_to_task_subscribers(local_task_id, ws_message)
            
            logger.debug(f"发送 WebSocket 消息: type={ws_message.get('type')}, task_id={task_id}")
    
    logger.info(f"回放完成: local_task_id={local_task_id}")


@router.post(
    "/video/tasks/replay",
    response_model=ReplayResponse,
    summary="回放历史视频生成任务",
    description="基于 tasks.json 中的历史数据，回放视频生成任务的完整流程"
)
async def replay_video_task(
    request: ReplayRequest,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    settings=Depends(get_settings),
):
    """
    回放历史视频生成任务
    
    从 tasks.json 中读取指定任务的历史数据，按照时间顺序回放所有 webhook 事件，
    通过 WebSocket 发送给前端，模拟完整的视频生成流程。
    """
    try:
        # 1. 加载 tasks.json
        tasks_data = load_tasks_json(settings)
        
        # 2. 查找任务
        task_data = tasks_data.get(request.task_id)
        if not task_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {request.task_id}"
            )
        
        # 3. 检查是否是视频生成任务
        metadata = task_data.get("metadata", {})
        if metadata.get("task_type") != "video_generation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"任务 {request.task_id} 不是视频生成任务"
            )
        
        # 4. 解析 webhook_events
        script_task_id, video_task_id, sorted_events = parse_webhook_events(task_data)
        
        if not script_task_id or not video_task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法从任务数据中提取 script_task_id 或 video_task_id"
            )
        
        if not sorted_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务没有 webhook_events 数据"
            )
        
        # 5. 确定本地任务 ID
        local_task_id = request.local_task_id or request.task_id
        
        # 6. 检查本地任务是否存在，如果不存在则创建
        existing_task = await tracker.get(local_task_id)
        if not existing_task:
            # 创建任务记录
            prompt = task_data.get("prompt", f"Replay video task: {request.task_id}")
            local_task = await tracker.create(
                prompt=prompt,
                attachments=[],
            )
            local_task_id = local_task.id
            
            # 更新任务元数据
            await tracker.update(
                local_task_id,
                manus_task_id=script_task_id,  # 初始设置为 script_task_id
                metadata=metadata,
                status="processing"
            )
            logger.info(f"创建本地任务记录: local_task_id={local_task_id}")
        else:
            # 更新任务状态为 processing
            await tracker.update(
                local_task_id,
                status="processing"
            )
            logger.info(f"使用现有任务记录: local_task_id={local_task_id}")
        
        # 7. 订阅任务（确保消息能发送到前端）
        # 如果没有指定 client_id，我们仍然需要确保任务被订阅
        # 前端在收到 script_generation_completed 时会自动订阅 video_task_id
        if request.client_id and manager.is_connected(request.client_id):
            await manager.subscribe_task(request.client_id, local_task_id)
            await manager.subscribe_task(request.client_id, script_task_id)
            await manager.subscribe_task(request.client_id, video_task_id)
            logger.info(f"已订阅任务: client_id={request.client_id}")
        else:
            # 如果没有 client_id 或客户端未连接，记录警告
            # 前端应该已经订阅了 local_task_id，在收到消息后会自动订阅其他任务
            logger.warning(f"未找到客户端连接，前端需要先订阅 local_task_id={local_task_id}")
        
        # 8. 计算预计持续时间
        if len(sorted_events) > 1:
            first_time = datetime.fromisoformat(sorted_events[0]["timestamp"].replace("Z", "+00:00"))
            last_time = datetime.fromisoformat(sorted_events[-1]["timestamp"].replace("Z", "+00:00"))
            total_duration = (last_time - first_time).total_seconds()
            estimated_duration = total_duration / request.speed
        else:
            estimated_duration = 0.0
        
        # 9. 异步启动回放任务（不阻塞响应）
        asyncio.create_task(
            replay_webhook_events(
                local_task_id=local_task_id,
                script_task_id=script_task_id,
                video_task_id=video_task_id,
                events=sorted_events,
                speed=request.speed,
            )
        )
        
        # 10. 在回放完成后更新任务状态和视频路径
        async def update_task_status_on_complete():
            # 等待回放完成（估算时间）
            await asyncio.sleep(estimated_duration + 2)
            
            # 更新任务状态为完成
            task = await tracker.get(local_task_id)
            if task:
                metadata = task.metadata or {}
                
                # 如果没有 video_path，尝试设置测试视频路径
                if not metadata.get("video_path"):
                    test_video_paths = [
                        Path("static/test/sample_video.mp4"),
                        Path("./static/test/sample_video.mp4"),
                        Path(__file__).parent.parent.parent.parent / "static" / "test" / "sample_video.mp4",
                    ]
                    
                    for test_path in test_video_paths:
                        if test_path.exists():
                            metadata["video_path"] = str(test_path.resolve())
                            logger.info(f"设置测试视频路径: {metadata['video_path']}")
                            break
                
                # 更新任务状态和元数据
                await tracker.update(
                    local_task_id, 
                    status="completed",
                    metadata=metadata
                )
                logger.info(f"任务状态已更新为完成: local_task_id={local_task_id}")
        
        asyncio.create_task(update_task_status_on_complete())
        
        return ReplayResponse(
            success=True,
            message="回放任务已启动",
            local_task_id=local_task_id,
            script_task_id=script_task_id,
            video_task_id=video_task_id,
            total_events=len(sorted_events),
            estimated_duration=estimated_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回放任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回放任务失败: {str(e)}"
        )


@router.get(
    "/video/tasks/available",
    summary="获取可回放的任务列表",
    description="列出 tasks.json 中所有可回放的视频生成任务"
)
async def list_replayable_tasks(settings=Depends(get_settings)):
    """获取可回放的任务列表"""
    try:
        tasks_data = load_tasks_json(settings)
        
        replayable_tasks = []
        for task_id, task_data in tasks_data.items():
            # 处理 metadata 可能为 None 的情况
            metadata = task_data.get("metadata") or {}
            
            # 只处理视频生成任务
            if metadata.get("task_type") == "video_generation":
                webhook_events = task_data.get("webhook_events", [])
                if webhook_events:
                    replayable_tasks.append({
                        "task_id": task_id,
                        "topic": metadata.get("topic", "Unknown"),
                        "duration": metadata.get("duration"),
                        "style": metadata.get("style"),
                        "target_audience": metadata.get("target_audience"),
                        "status": task_data.get("status"),
                        "event_count": len(webhook_events),
                        "created_at": task_data.get("created_at"),
                    })
        
        return {
            "success": True,
            "data": replayable_tasks,
            "total": len(replayable_tasks)
        }
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {str(e)}"
        )
