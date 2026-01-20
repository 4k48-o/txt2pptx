"""
Video Generation Service - 视频生成服务

负责完整的视频生成流程，包括脚本生成和视频生成两个步骤
"""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import aiofiles
import httpx

from ...manus_client import AsyncManusClient, AsyncTaskManager, AsyncFileManager
from ...config import get_settings
from ...services import TaskTrackerService
from .script_service import VideoScriptService
from .markdown_parser import MarkdownParser, MarkdownValidator

logger = logging.getLogger(__name__)


class VideoGenerationService:
    """视频生成服务"""

    def __init__(
        self,
        client: AsyncManusClient,
        tracker: Optional[TaskTrackerService] = None,
    ):
        """
        初始化视频生成服务

        Args:
            client: 异步 Manus API 客户端实例
            tracker: 任务追踪服务（可选）
        """
        self.client = client
        self.task_manager = AsyncTaskManager(client)
        self.file_manager = AsyncFileManager(client)
        self.script_service = VideoScriptService(client)
        self.tracker = tracker
        self.settings = get_settings()

    async def generate_video(
        self,
        topic: str,
        duration: int,
        style: str,
        target_audience: str,
        local_task_id: str,
    ) -> Dict[str, Any]:
        """
        完整视频生成流程（主入口）

        Args:
            topic: 视频主题
            duration: 视频时长（秒）
            style: 视频风格
            target_audience: 目标受众
            local_task_id: 本地任务 ID

        Returns:
            包含 script_task_id 的字典

        Raises:
            RuntimeError: 脚本生成任务创建失败
            ManusAPIException: Manus API 调用失败
        """
        logger.info(
            f"[视频生成] 开始视频生成流程: topic={topic}, duration={duration}s, "
            f"style={style}, audience={target_audience}, local_task_id={local_task_id}"
        )

        try:
            # 1. 调用脚本生成服务
            logger.info(f"[视频生成] 步骤 1/2: 创建脚本生成任务...")
            script_result = await self.script_service.generate_video_plan(
                topic=topic,
                duration=duration,
                style=style,
                target_audience=target_audience,
            )

            script_task_id = script_result.get("task_id")

            if not script_task_id:
                logger.error(f"[视频生成] 脚本生成任务创建失败: 未返回 task_id")
                raise RuntimeError("脚本生成任务创建失败")

            logger.info(f"[视频生成] 脚本生成任务已创建: script_task_id={script_task_id}")

            # 更新本地任务元数据（包括 Manus 任务 ID）
            if self.tracker:
                logger.debug(f"[视频生成] 更新本地任务元数据: local_task_id={local_task_id}")
                task = await self.tracker.get(local_task_id)
                if task:
                    metadata = task.metadata or {}
                    metadata.update({
                        "task_type": "video_generation",
                        "step": "script_generation",
                        "script_task_id": script_task_id,
                        "topic": topic,
                        "duration": duration,
                        "style": style,
                        "target_audience": target_audience,
                    })
                    # 同时更新 manus_task_id，以便 webhook 能够找到本地任务
                    await self.tracker.update(
                        local_task_id,
                        manus_task_id=script_task_id,
                        metadata=metadata
                    )
                    logger.debug(f"[视频生成] 本地任务元数据已更新，manus_task_id={script_task_id}")

            logger.info(f"[视频生成] 视频生成流程初始化完成: script_task_id={script_task_id}")
            return {
                "script_task_id": script_task_id,
                "local_task_id": local_task_id,
            }
            
        except Exception as e:
            logger.error(
                f"[视频生成] 视频生成流程初始化失败: local_task_id={local_task_id}, "
                f"error={type(e).__name__}: {e}",
                exc_info=True
            )
            # 更新任务状态为失败
            if self.tracker:
                try:
                    await self.tracker.update(
                        local_task_id,
                        status="failed",
                        error=f"视频生成流程初始化失败: {str(e)}"
                    )
                except Exception as update_error:
                    logger.error(f"[视频生成] 更新任务状态失败: {update_error}")
            raise

    async def handle_script_generation_complete(
        self,
        local_task_id: str,
        script_task_id: str,
    ) -> Dict[str, Any]:
        """
        处理脚本生成完成（由 Webhook 调用）

        Args:
            local_task_id: 本地任务 ID
            script_task_id: 脚本生成任务 ID

        Returns:
            包含 video_task_id 的字典

        Raises:
            RuntimeError: 任务处理失败
            ManusAPIException: Manus API 调用失败
        """
        logger.info(
            f"[视频生成] 处理脚本生成完成: local_task_id={local_task_id}, script_task_id={script_task_id}"
        )

        try:
            # 1. 获取任务元数据
            if not self.tracker:
                raise RuntimeError("TaskTrackerService 未初始化")

            logger.debug(f"[视频生成] 获取本地任务信息: local_task_id={local_task_id}")
            task = await self.tracker.get(local_task_id)
            if not task:
                raise RuntimeError(f"本地任务不存在: {local_task_id}")

            metadata = task.metadata or {}
            duration = metadata.get("duration")
            style = metadata.get("style")

            if not duration or not style:
                logger.error(f"[视频生成] 任务元数据不完整: duration={duration}, style={style}")
                raise RuntimeError("任务元数据中缺少 duration 或 style")

            logger.debug(f"[视频生成] 任务参数: duration={duration}s, style={style}")

            # 2. 获取脚本生成任务结果（带重试）
            from ...utils.retry import retry_async, RetryConfig
            
            retry_config = RetryConfig(
                max_retries=3,
                initial_delay=1.0,
                max_delay=30.0,
            )
            
            logger.info(f"[视频生成] 获取脚本生成任务结果: script_task_id={script_task_id}")
            # 使用 lambda 包装以正确传递参数
            script_task_result = await retry_async(
                lambda: self.task_manager.get_task(script_task_id),
                config=retry_config,
                operation_name="获取脚本生成任务结果",
            )

            # 3. 从任务结果中提取 Markdown 文件信息（file_id 或 fileUrl）
            logger.info("[视频生成] 提取 Markdown 文件信息...")
            file_id, file_url, markdown_filename = self._extract_markdown_file_info(script_task_result)
            
            # 构建附件信息
            attachment = None
            markdown_path = None  # 初始化变量
            
            if file_id:
                # 优先使用 file_id（直接从云端使用，无需下载）
                logger.info(f"[视频生成] 使用 file_id: {file_id}，直接从云端使用 Markdown 文件")
                attachment = {
                    "filename": markdown_filename or f"video_plan_{script_task_id[:8]}.md",
                    "file_id": file_id
                }
            elif file_url:
                # 如果没有 file_id，使用 fileUrl（Manus API 支持直接使用 URL）
                logger.info(f"[视频生成] 使用 fileUrl: {file_url[:80]}...，直接从云端使用 Markdown 文件")
                attachment = {
                    "filename": markdown_filename or f"video_plan_{script_task_id[:8]}.md",
                    "url": file_url,
                    "mimeType": "text/markdown"
                }
            else:
                # 如果都没有，下载文件并上传（后备方案）
                logger.warning("[视频生成] 未找到 file_id 或 fileUrl，将下载并上传 Markdown 文件")
                markdown_content = await self.script_service._extract_markdown(script_task_result)
                markdown_path = await self.script_service._save_markdown(
                    markdown_content, script_task_id
                )
                markdown_filename = markdown_path.name
                
                # 上传 Markdown 文件到 Manus（带重试）
                logger.info("[视频生成] 上传 Markdown 文件到 Manus...")
                file_result = await retry_async(
                    lambda: self._upload_markdown_file(markdown_path),
                    config=retry_config,
                    operation_name="上传 Markdown 文件",
                )
                file_id = file_result.get("file_id")
                
                if not file_id:
                    logger.error(f"[视频生成] Markdown 文件上传失败: {file_result}")
                    raise RuntimeError("Markdown 文件上传失败")
                
                logger.info(f"[视频生成] Markdown 文件上传成功: file_id={file_id}")
                attachment = {
                    "filename": markdown_filename,
                    "file_id": file_id
                }
            
            # 保存本地副本（用于记录，可选，不影响主流程）
            if not markdown_path and (file_id or file_url):
                try:
                    # 如果有 file_id 或 fileUrl，下载一份本地副本用于记录
                    markdown_content = await self.script_service._extract_markdown(script_task_result)
                    markdown_path = await self.script_service._save_markdown(
                        markdown_content, script_task_id
                    )
                    logger.info(f"[视频生成] Markdown 文件已保存（本地副本）: {markdown_path}")
                except Exception as e:
                    logger.warning(f"[视频生成] 保存本地副本失败（不影响流程）: {e}")

            # 4. 构建视频生成 prompt
            logger.debug("[视频生成] 构建视频生成 prompt...")
            prompt = self._build_video_generation_prompt(duration, style)

            # 5. 创建视频生成任务（带重试）
            logger.info("[视频生成] 创建视频生成任务...")
            # 使用 lambda 包装以正确传递参数
            video_task_result = await retry_async(
                lambda: self.task_manager.create_task(
                    prompt=prompt,
                    attachments=[attachment],
                ),
                config=retry_config,
                operation_name="创建视频生成任务",
            )

            video_task_id = video_task_result.get("task_id") or video_task_result.get("id")

            if not video_task_id:
                logger.error(f"[视频生成] 视频生成任务创建失败: 未返回 task_id, 响应: {video_task_result}")
                raise RuntimeError("视频生成任务创建失败")

            logger.info(f"[视频生成] 视频生成任务已创建: video_task_id={video_task_id}")

            # 6. 更新任务元数据
            logger.debug(f"[视频生成] 更新任务元数据: local_task_id={local_task_id}")
            metadata_update = {
                "step": "video_generation",
                "video_task_id": video_task_id,
            }
            # 如果有本地保存的 markdown_path，记录它
            if 'markdown_path' in locals() and markdown_path:
                metadata_update["markdown_path"] = str(markdown_path)
            # 记录 file_id 或 fileUrl
            if file_id:
                metadata_update["markdown_file_id"] = file_id
            elif file_url:
                metadata_update["markdown_file_url"] = file_url
            
            metadata.update(metadata_update)
            await self.tracker.update(local_task_id, metadata=metadata)
            logger.debug("[视频生成] 任务元数据已更新")

            logger.info(
                f"[视频生成] 脚本生成完成处理成功: video_task_id={video_task_id}"
            )

            result = {
                "video_task_id": video_task_id,
                "local_task_id": local_task_id,
            }
            # 如果有本地保存的 markdown_path，添加到返回值
            if markdown_path:
                result["markdown_path"] = str(markdown_path)
            
            return result
            
        except Exception as e:
            logger.error(
                f"[视频生成] 处理脚本生成完成失败: local_task_id={local_task_id}, "
                f"script_task_id={script_task_id}, error={type(e).__name__}: {e}",
                exc_info=True
            )
            # 更新任务状态为失败
            if self.tracker:
                try:
                    await self.tracker.update(
                        local_task_id,
                        status="failed",
                        error=f"处理脚本生成完成失败: {str(e)}"
                    )
                except Exception as update_error:
                    logger.error(f"[视频生成] 更新任务状态失败: {update_error}")
            raise

    async def handle_video_generation_complete(
        self,
        local_task_id: str,
        video_task_id: str,
    ) -> Dict[str, Any]:
        """
        处理视频生成完成（由 Webhook 调用）

        Args:
            local_task_id: 本地任务 ID
            video_task_id: 视频生成任务 ID

        Returns:
            包含 video_path 的字典

        Raises:
            RuntimeError: 任务处理失败
            ManusAPIException: Manus API 调用失败
            FileNotFoundError: 视频文件不存在
        """
        logger.info(
            f"[视频生成] 处理视频生成完成: local_task_id={local_task_id}, video_task_id={video_task_id}"
        )

        try:
            # 1. 获取任务元数据
            if not self.tracker:
                raise RuntimeError("TaskTrackerService 未初始化")

            logger.debug(f"[视频生成] 获取本地任务信息: local_task_id={local_task_id}")
            task = await self.tracker.get_task(local_task_id)
            if not task:
                raise RuntimeError(f"本地任务不存在: {local_task_id}")

            metadata = task.metadata or {}
            duration = metadata.get("duration")

            if not duration:
                logger.error(f"[视频生成] 任务元数据中缺少 duration")
                raise RuntimeError("任务元数据中缺少 duration")

            logger.debug(f"[视频生成] 任务参数: duration={duration}s")

            # 2. 获取视频生成任务结果（带重试）
            from ...utils.retry import retry_async, RetryConfig
            
            retry_config = RetryConfig(
                max_retries=3,
                initial_delay=1.0,
                max_delay=30.0,
            )
            
            logger.info(f"[视频生成] 获取视频生成任务结果: video_task_id={video_task_id}")
            # 使用 lambda 包装以正确传递参数
            video_task_result = await retry_async(
                lambda: self.task_manager.get_task(video_task_id),
                config=retry_config,
                operation_name="获取视频生成任务结果",
            )

            # 3. 下载视频文件（带重试）
            logger.info("[视频生成] 开始下载视频文件...")
            # 使用 lambda 包装以正确传递参数
            video_path = await retry_async(
                lambda: self._download_video_file(
                    video_task_result,
                    local_task_id,
                    duration,
                ),
                config=RetryConfig(
                    max_retries=3,
                    initial_delay=2.0,
                    max_delay=60.0,
                ),
                operation_name="下载视频文件",
            )

            logger.info(f"[视频生成] 视频文件下载成功: {video_path}")

            # 4. 更新任务元数据
            logger.debug(f"[视频生成] 更新任务元数据: local_task_id={local_task_id}")
            metadata.update({
                "step": "completed",
                "video_path": str(video_path),
            })
            await self.tracker.update(local_task_id, metadata=metadata)
            logger.debug("[视频生成] 任务元数据已更新")

            logger.info(
                f"[视频生成] 视频生成完成处理成功: video_path={video_path}"
            )

            return {
                "video_path": str(video_path),
                "local_task_id": local_task_id,
            }
            
        except Exception as e:
            logger.error(
                f"[视频生成] 处理视频生成完成失败: local_task_id={local_task_id}, "
                f"video_task_id={video_task_id}, error={type(e).__name__}: {e}",
                exc_info=True
            )
            # 更新任务状态为失败
            if self.tracker:
                try:
                    await self.tracker.update(
                        local_task_id,
                        status="failed",
                        error=f"处理视频生成完成失败: {str(e)}"
                    )
                except Exception as update_error:
                    logger.error(f"[视频生成] 更新任务状态失败: {update_error}")
            raise

    def _build_video_generation_prompt(
        self,
        duration: int,
        style: str,
    ) -> str:
        """
        构建视频生成 prompt

        Args:
            duration: 视频时长（秒），来自前端用户选择
            style: 视频风格，来自前端用户选择

        Returns:
            完整的 prompt 字符串
        """
        prompt_parts = [
            "Generate a professional video file based on the attached Markdown video production plan.",
            "",
            "=== ATTACHMENT ===",
            "The attached Markdown file contains a complete video production plan with:",
            "- Title and Description (including target audience and style)",
            "- Detailed Script with scene-by-scene narration and timing",
            "- Storyboard with visual elements, composition, and design specifications",
            "- Background Music recommendations with style, tempo, mood, and duration",
            "",
            "=== CRITICAL REQUIREMENTS ===",
            "",
            f"1. VIDEO DURATION (MOST IMPORTANT):",
            f"   - The video MUST be EXACTLY {duration} seconds long",
            f"   - This duration is specified by the user and MUST match the Duration in the Background Music section",
            f"   - The total video length must be precisely {duration} seconds (not {duration-1} or {duration+1})",
            "",
            f"2. VIDEO STYLE:",
            f"   - The video style MUST be: {style}",
            f"   - This style is specified by the user and MUST match the style described in the Markdown Description section",
            f"   - Apply {style} style consistently throughout all scenes",
            "",
            "3. SCRIPT ADHERENCE:",
            "   - Follow the Script section EXACTLY for narration text and scene timing",
            "   - Each scene's narration must match the text in the Script section",
            "   - Scene timing must match the time ranges specified (e.g., 0:00-0:15)",
            "   - Scene transitions must occur at the exact times specified",
            "",
            "4. STORYBOARD ADHERENCE:",
            "   - Follow the Storyboard section EXACTLY for all visual elements",
            "   - Composition must match the Storyboard descriptions",
            "   - Color schemes must match the Storyboard specifications",
            "   - Visual effects must match the Storyboard requirements",
            "   - Design style must match the Storyboard descriptions",
            "   - Text overlays must match the Storyboard specifications (if any)",
            "   - Animations must match the Storyboard descriptions",
            "",
            "5. BACKGROUND MUSIC:",
            "   - Use the Background Music recommendations from the Markdown file",
            "   - Music style must match the recommended Style",
            "   - Tempo, mood, and energy level must match the Characteristics",
            f"   - Music duration MUST be EXACTLY {duration} seconds (matching video duration)",
            "   - Music volume must be at background level and not overpower narration",
            "",
            "=== OUTPUT SPECIFICATIONS ===",
            "- Video format: MP4 (H.264 codec recommended)",
            "- Resolution: 1920x1080 (Full HD) minimum, higher preferred",
            "- Frame rate: 30 fps (or 24/25 fps if appropriate for style)",
            "- Audio:",
            "  * Include clear, synchronized narration matching the Script",
            "  * Include background music matching the Background Music recommendations",
            "  * Ensure proper audio mixing (narration clear, music at appropriate level)",
            "- Aspect ratio: 16:9 (standard widescreen)",
            "",
            "=== QUALITY STANDARDS ===",
            "- Visual quality: High definition, professional production quality",
            "- Narration:",
            "  * Clear, natural-sounding voice",
            "  * Properly synchronized with visuals",
            "  * Appropriate pacing for the target audience",
            "- Visuals:",
            "  * High-quality graphics, animations, or footage",
            "  * Smooth transitions between scenes",
            "  * Professional composition and framing",
            "  * Consistent visual style throughout",
            "- Audio:",
            "  * Clear narration without background noise",
            "  * Background music that complements but doesn't compete with narration",
            "  * Proper audio levels and mixing",
            "- Overall:",
            "  * Professional, polished production",
            "  * Engaging and appropriate for the target audience",
            "  * Matches the {style} style consistently",
            "",
            "=== IMPORTANT NOTES ===",
            f"- The video duration of {duration} seconds is a user-specified requirement and MUST be exact",
            f"- The {style} style is a user-specified requirement and MUST be applied consistently",
            "- All content must be appropriate for the target audience specified in the Description",
            "- The video should be production-ready and suitable for professional use",
            "",
            "Please generate the video file following the Markdown plan exactly, ensuring all requirements are met.",
        ]

        return "\n".join(prompt_parts)

    def _extract_markdown_file_info(
        self,
        task_result: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        从任务结果中提取 Markdown 文件信息（file_id、fileUrl、filename）

        Args:
            task_result: Manus API 返回的任务结果

        Returns:
            (file_id, file_url, filename) 元组，如果未找到则返回 (None, None, None)
        """
        # Manus API 返回的结构：output 字段包含消息列表
        outputs = task_result.get("output", task_result.get("outputs", []))

        # 遍历 output 消息，查找文件类型的输出
        for output in outputs:
            content = output.get("content", [])
            for item in content:
                item_type = item.get("type", "")
                # 查找 output_file 类型（Markdown 文件）
                if item_type == "output_file":
                    file_name = item.get("fileName") or item.get("file_name")
                    mime_type = item.get("mimeType") or item.get("mime_type")
                    
                    # 检查是否是 Markdown 文件
                    if file_name and (file_name.endswith(".md") or mime_type == "text/markdown"):
                        # 检查是否有 file_id 字段
                        file_id = item.get("file_id") or item.get("fileId") or item.get("id")
                        file_url = item.get("fileUrl") or item.get("file_url")
                        
                        if file_id:
                            logger.info(f"[视频生成] 从任务结果中找到 file_id: {file_id}, filename: {file_name}")
                            return (file_id, None, file_name)
                        elif file_url:
                            logger.info(f"[视频生成] 从任务结果中找到 fileUrl: {file_url[:80]}..., filename: {file_name}")
                            return (None, file_url, file_name)
                elif item_type in ["file", "artifact"]:
                    file_name = item.get("fileName") or item.get("file_name")
                    file_id = item.get("file_id") or item.get("fileId") or item.get("id")
                    file_url = item.get("fileUrl") or item.get("file_url")
                    
                    if file_id:
                        logger.info(f"[视频生成] 从任务结果中找到 file_id: {file_id}, filename: {file_name}")
                        return (file_id, None, file_name)
                    elif file_url:
                        logger.info(f"[视频生成] 从任务结果中找到 fileUrl: {file_url[:80]}..., filename: {file_name}")
                        return (None, file_url, file_name)

        logger.debug("[视频生成] 任务结果中未找到 Markdown 文件信息")
        return (None, None, None)

    def _extract_filename_from_task_result(
        self,
        task_result: Dict[str, Any],
    ) -> Optional[str]:
        """
        从任务结果中提取文件名

        Args:
            task_result: Manus API 返回的任务结果

        Returns:
            文件名，如果未找到则返回 None
        """
        outputs = task_result.get("output", task_result.get("outputs", []))

        for output in outputs:
            content = output.get("content", [])
            for item in content:
                item_type = item.get("type", "")
                if item_type == "output_file":
                    file_name = item.get("fileName") or item.get("file_name") or item.get("filename")
                    if file_name:
                        return file_name
                elif item_type in ["file", "artifact"]:
                    file_name = item.get("fileName") or item.get("file_name") or item.get("filename")
                    if file_name:
                        return file_name

        return None

    async def _upload_markdown_file(
        self,
        markdown_path: Path,
    ) -> Dict[str, Any]:
        """
        上传 Markdown 文件到 Manus

        Args:
            markdown_path: Markdown 文件路径

        Returns:
            包含 file_id 的响应

        Raises:
            FileNotFoundError: 文件不存在
            ManusAPIException: 上传失败
        """
        logger.info(f"[文件操作] 上传 Markdown 文件: {markdown_path}")

        if not markdown_path.exists():
            logger.error(f"[文件操作] Markdown 文件不存在: {markdown_path}")
            raise FileNotFoundError(f"Markdown 文件不存在: {markdown_path}")

        file_size = markdown_path.stat().st_size
        logger.debug(f"[文件操作] 文件大小: {file_size} 字节")

        try:
            # 使用 AsyncFileManager 上传文件
            result = await self.file_manager.upload_file(str(markdown_path))
            file_id = result.get('file_id')
            
            if not file_id:
                logger.error(f"[文件操作] 上传失败: 未返回 file_id, 响应: {result}")
                raise RuntimeError("Markdown 文件上传失败: 未返回 file_id")

            logger.info(f"[文件操作] Markdown 文件上传成功: file_id={file_id}, size={file_size} 字节")
            return result
            
        except Exception as e:
            logger.error(
                f"[文件操作] Markdown 文件上传失败: {markdown_path}, error={type(e).__name__}: {e}",
                exc_info=True
            )
            raise

    async def _download_video_file(
        self,
        task_result: Dict[str, Any],
        local_task_id: str,
        expected_duration: int,
    ) -> Path:
        """
        下载生成的视频文件

        Args:
            task_result: Manus API 返回的任务结果
            local_task_id: 本地任务 ID（用于生成文件名）
            expected_duration: 期望的视频时长（秒）

        Returns:
            保存的视频文件路径
        """
        logger.info("下载视频文件...")

        # 从任务结果中提取视频文件 URL
        outputs = task_result.get("output", task_result.get("outputs", []))

        video_url = None
        file_name = None

        # 遍历 output 消息，查找文件类型的输出
        for output in outputs:
            content = output.get("content", [])
            for item in content:
                item_type = item.get("type", "")
                # 查找 output_file 类型
                if item_type == "output_file":
                    url = item.get("fileUrl", item.get("url", item.get("file_url", "")))
                    file_name = item.get("fileName", item.get("filename", ""))
                    if url:
                        video_url = url
                        break
                elif item_type in ["file", "artifact", "video"]:
                    url = item.get("fileUrl", item.get("url", ""))
                    if url:
                        video_url = url
                        break
            if video_url:
                break

        if not video_url:
            # 尝试从其他字段获取
            video_url = (
                task_result.get("output_url")
                or task_result.get("result_url")
                or task_result.get("download_url")
            )

        if not video_url:
            logger.error(f"任务结果: {task_result}")
            raise RuntimeError(
                "未找到视频下载链接。请检查日志中的任务详情。"
            )

        # 确定输出文件名
        if not file_name:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"video_{local_task_id[:8]}_{timestamp}.mp4"
        elif not file_name.endswith(".mp4"):
            file_name += ".mp4"

        video_path = self.settings.video_storage_dir / file_name

        # 确保目录存在
        video_path.parent.mkdir(parents=True, exist_ok=True)

        # 下载文件
        logger.info(f"[文件操作] 从 {video_url[:80]}... 下载视频")
        logger.info(f"[文件操作] 保存到: {video_path}")

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
                logger.debug(f"[文件操作] 开始下载，URL: {video_url}")
                response = await client.get(video_url)
                response.raise_for_status()
                
                content_length = len(response.content)
                logger.debug(f"[文件操作] 下载完成，大小: {content_length} 字节")

                async with aiofiles.open(video_path, "wb") as f:
                    await f.write(response.content)
                
                logger.info(f"[文件操作] 视频文件已保存: {video_path} ({content_length} 字节)")
                
        except httpx.TimeoutException as e:
            logger.error(f"[文件操作] 下载视频超时: {video_url}, error={e}")
            raise RuntimeError(f"下载视频超时: {e}") from e
        except httpx.HTTPError as e:
            logger.error(f"[文件操作] 下载视频失败: {video_url}, error={type(e).__name__}: {e}")
            raise RuntimeError(f"下载视频失败: {e}") from e
        except IOError as e:
            logger.error(f"[文件操作] 保存视频文件失败: {video_path}, error={e}")
            raise RuntimeError(f"保存视频文件失败: {e}") from e

        # 验证视频时长（如果可能）
        # 注意：这里只是占位，实际需要安装 ffprobe 或使用其他工具
        # video_duration = await self._get_video_duration(video_path)
        # if video_duration and abs(video_duration - expected_duration) > 2:
        #     logger.warning(
        #         f"视频时长 ({video_duration}s) 与期望时长 ({expected_duration}s) 差异较大"
        #     )

        return video_path

    async def _get_video_duration(
        self,
        video_path: Path,
    ) -> Optional[int]:
        """
        获取视频时长（秒）

        需要安装 ffprobe 或使用其他工具

        Args:
            video_path: 视频文件路径

        Returns:
            视频时长（秒），如果无法获取则返回 None
        """
        # TODO: 实现视频时长检测
        # 可以使用 ffprobe 或其他工具
        # import subprocess
        # result = subprocess.run(
        #     ["ffprobe", "-v", "error", "-show_entries", "format=duration",
        #      "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        #     capture_output=True, text=True
        # )
        # if result.returncode == 0:
        #     return int(float(result.stdout.strip()))
        return None
