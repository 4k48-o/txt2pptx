"""
Video API - 视频生成 API 接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.video import VideoTaskRequest, VideoTaskResponse, VideoTaskStatus
from ..schemas.common import APIResponse
from ..config import get_settings
from ..dependencies import get_task_tracker, get_manus_client
from ..services import TaskTrackerService
from ..manus_client import AsyncManusClient
from ..services.video import VideoGenerationService
from ..websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/video/tasks", tags=["video"])


@router.post(
    "",
    response_model=APIResponse[VideoTaskResponse],
    summary="创建视频生成任务",
    description="创建视频生成任务，包括脚本生成和视频生成两个步骤",
)
async def create_video_task(
    request: VideoTaskRequest,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    settings=Depends(get_settings),
):
    """
    创建视频生成任务

    - **topic**: 视频主题（用户输入的文本描述）
    - **duration**: 视频时长（秒），前端用户选择（5-30秒）
    - **style**: 视频风格，前端用户选择
    - **target_audience**: 目标受众，前端用户选择
    - **client_id**: WebSocket 客户端 ID（可选）

    任务创建后会进入脚本生成阶段，完成后自动进入视频生成阶段。
    """
    try:
        logger.info(
            f"创建视频生成任务: topic={request.topic}, "
            f"duration={request.duration}, style={request.style}, "
            f"audience={request.target_audience}, client_id={request.client_id}"
        )

        # 1. 验证 style 和 target_audience 是否在支持的列表中
        if request.style not in settings.video_supported_styles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的视频风格: {request.style}。支持的风格: {settings.video_supported_styles}",
            )

        if request.target_audience not in settings.video_supported_audiences:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的目标受众: {request.target_audience}。支持的受众: {settings.video_supported_audiences}",
            )

        # 2. 检查 Webhook 是否启用
        if not settings.webhook_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook 模式未启用，视频生成需要 Webhook 支持。请配置 WEBHOOK_ENABLED=true",
            )

        # 3. 创建本地任务记录（参数自动保存到 metadata）
        # 构建 prompt（用于任务记录）
        prompt = f"Generate video: {request.topic} ({request.duration}s, {request.style}, {request.target_audience})"

        local_task = await tracker.create(
            prompt=prompt,
            attachments=[],
        )

        # 保存视频生成相关参数到 metadata
        metadata = {
            "task_type": "video_generation",
            "step": "script_generation",
            "topic": request.topic,
            "duration": request.duration,
            "style": request.style,
            "target_audience": request.target_audience,
        }
        if request.client_id:
            metadata["client_id"] = request.client_id

        await tracker.update(
            local_task.id,
            metadata=metadata,
            status="processing",
        )

        # 4. 订阅 WebSocket 更新
        if request.client_id and manager.is_connected(request.client_id):
            await manager.subscribe_task(request.client_id, local_task.id)
            logger.info(f"已订阅任务更新: client_id={request.client_id}, task_id={local_task.id}")

        # 5. 调用视频生成服务启动脚本生成（参数从 metadata 中获取）
        async for client in get_manus_client():
            video_service = VideoGenerationService(client, tracker)

            try:
                result = await video_service.generate_video(
                    topic=request.topic,
                    duration=request.duration,
                    style=request.style,
                    target_audience=request.target_audience,
                    local_task_id=local_task.id,
                )

                script_task_id = result.get("script_task_id")

                # 订阅脚本生成任务 ID
                if request.client_id and manager.is_connected(request.client_id) and script_task_id:
                    await manager.subscribe_task(request.client_id, script_task_id)
                    logger.info(f"已订阅脚本生成任务: client_id={request.client_id}, script_task_id={script_task_id}")

                # 更新 metadata 中的 script_task_id
                metadata["script_task_id"] = script_task_id
                await tracker.update(local_task.id, metadata=metadata)

                logger.info(f"视频生成任务已创建: local_task_id={local_task.id}, script_task_id={script_task_id}")

                # 6. 返回任务 ID 和状态
                return APIResponse(
                    success=True,
                    data=VideoTaskResponse(
                        task_id=local_task.id,
                        status=VideoTaskStatus.PROCESSING,
                        step="script_generation",
                        message="任务创建成功，脚本生成中",
                    ),
                    message="视频生成任务创建成功",
                )

            finally:
                await client.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建视频生成任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}",
        )


@router.get(
    "/{task_id}",
    response_model=APIResponse[VideoTaskResponse],
    summary="查询视频生成任务",
    description="查询视频生成任务的详细信息，包括状态、当前步骤、下载链接等",
)
async def get_video_task(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    settings=Depends(get_settings),
):
    """
    查询视频生成任务

    - **task_id**: 任务 ID（本地任务 ID）
    """
    try:
        logger.info(f"查询视频生成任务: task_id={task_id}")

        # 1. 查询任务信息
        task = await tracker.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}",
            )

        # 2. 检查是否是视频生成任务
        metadata = task.metadata or {}
        task_type = metadata.get("task_type")
        if task_type != "video_generation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"任务 {task_id} 不是视频生成任务",
            )

        # 3. 获取任务状态、当前步骤
        task_step = metadata.get("step", "script_generation")
        
        # 映射本地状态到 VideoTaskStatus
        status_mapping = {
            "pending": VideoTaskStatus.PENDING,
            "processing": VideoTaskStatus.PROCESSING,
            "completed": VideoTaskStatus.COMPLETED,
            "failed": VideoTaskStatus.FAILED,
        }
        task_status = status_mapping.get(task.status, VideoTaskStatus.PENDING)

        # 4. 构建下载链接（如已完成）
        video_url = None
        markdown_url = None

        if task.status == "completed":
            video_path = metadata.get("video_path")
            if video_path:
                video_url = f"/api/v1/video/tasks/{task_id}/download"
            
            markdown_path = metadata.get("markdown_path")
            if markdown_path:
                markdown_url = f"/api/v1/video/tasks/{task_id}/markdown"

        # 5. 返回任务信息
        return APIResponse(
            success=True,
            data=VideoTaskResponse(
                task_id=task_id,
                status=task_status,
                step=task_step,
                video_url=video_url,
                markdown_url=markdown_url,
                message=f"任务状态: {task.status}, 当前步骤: {task_step}",
            ),
            message="查询成功",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询视频生成任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询任务失败: {str(e)}",
        )


@router.get(
    "/{task_id}/download",
    summary="下载生成的视频文件",
    description="下载视频生成任务完成的视频文件",
)
async def download_video(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    settings=Depends(get_settings),
):
    """
    下载生成的视频文件

    - **task_id**: 任务 ID（本地任务 ID）
    """
    from fastapi.responses import FileResponse
    from pathlib import Path

    try:
        logger.info(f"下载视频文件: task_id={task_id}")

        # 1. 查询任务信息
        task = await tracker.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}",
            )

        # 2. 验证任务状态（必须已完成）
        if task.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"任务尚未完成，当前状态: {task.status}",
            )

        # 3. 获取视频文件路径
        metadata = task.metadata or {}
        video_path_str = metadata.get("video_path")
        
        if not video_path_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="视频文件路径不存在",
            )

        video_path = Path(video_path_str)

        # 4. 验证文件是否存在
        if not video_path.exists():
            logger.error(f"视频文件不存在: {video_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="视频文件不存在",
            )

        # 5. 返回文件响应
        logger.info(f"返回视频文件: {video_path}")
        return FileResponse(
            path=str(video_path),
            filename=video_path.name,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="{video_path.name}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载视频文件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载文件失败: {str(e)}",
        )


@router.get(
    "/{task_id}/markdown",
    summary="下载 Markdown 文件",
    description="下载视频生成任务中的 Markdown 脚本文件",
)
async def download_markdown(
    task_id: str,
    tracker: TaskTrackerService = Depends(get_task_tracker),
    settings=Depends(get_settings),
):
    """
    下载 Markdown 文件

    - **task_id**: 任务 ID（本地任务 ID）
    """
    from fastapi.responses import FileResponse
    from pathlib import Path

    try:
        logger.info(f"下载 Markdown 文件: task_id={task_id}")

        # 1. 查询任务信息
        task = await tracker.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}",
            )

        # 2. 验证任务状态（脚本生成应该已完成）
        metadata = task.metadata or {}
        task_step = metadata.get("step")
        
        if task_step == "script_generation" and task.status not in ["completed", "processing"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"脚本尚未生成完成，当前状态: {task.status}",
            )

        # 3. 获取 Markdown 文件路径
        markdown_path_str = metadata.get("markdown_path")
        
        if not markdown_path_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Markdown 文件路径不存在",
            )

        markdown_path = Path(markdown_path_str)

        # 4. 验证文件是否存在
        if not markdown_path.exists():
            logger.error(f"Markdown 文件不存在: {markdown_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Markdown 文件不存在",
            )

        # 5. 返回文件响应
        logger.info(f"返回 Markdown 文件: {markdown_path}")
        return FileResponse(
            path=str(markdown_path),
            filename=markdown_path.name,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{markdown_path.name}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载 Markdown 文件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载文件失败: {str(e)}",
        )
