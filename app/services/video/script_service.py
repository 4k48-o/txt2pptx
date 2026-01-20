"""
Video Script Service - 视频脚本生成服务

负责生成视频制作计划（Markdown 格式），包括脚本、分镜和背景音乐推荐
"""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import aiofiles

from ...manus_client import AsyncManusClient, AsyncTaskManager
from ...config import get_settings
from .markdown_parser import MarkdownParser, MarkdownValidator

logger = logging.getLogger(__name__)


class VideoScriptService:
    """视频脚本生成服务"""

    def __init__(self, client: AsyncManusClient):
        """
        初始化视频脚本生成服务

        Args:
            client: 异步 Manus API 客户端实例
        """
        self.client = client
        self.task_manager = AsyncTaskManager(client)
        self.settings = get_settings()

    async def generate_video_plan(
        self,
        topic: str,
        duration: int,
        style: str,
        target_audience: str,
    ) -> Dict[str, Any]:
        """
        生成视频制作计划

        Args:
            topic: 视频主题（用户输入）
            duration: 视频时长（秒），前端用户选择
            style: 视频风格，前端用户选择
            target_audience: 目标受众，前端用户选择

        Returns:
            包含 task_id 和 markdown_path 的字典

        Raises:
            RuntimeError: 任务创建失败
            ManusAPIException: Manus API 调用失败
        """
        logger.info(
            f"[脚本生成] 开始生成视频制作计划: topic={topic}, duration={duration}s, "
            f"style={style}, audience={target_audience}"
        )

        try:
            # 1. 构建 prompt
            logger.debug("[脚本生成] 构建 prompt...")
            prompt = self._build_script_prompt(topic, duration, style, target_audience)
            logger.debug(f"[脚本生成] Prompt 构建完成，长度: {len(prompt)} 字符")

            # 2. 调用 Manus API 创建任务（带重试）
            from ...utils.retry import retry_async, RetryConfig
            
            retry_config = RetryConfig(
                max_retries=3,
                initial_delay=1.0,
                max_delay=30.0,
            )
            
            logger.info("[脚本生成] 调用 Manus API 创建脚本生成任务...")
            # 使用 lambda 包装以正确传递参数
            task_result = await retry_async(
                lambda: self.task_manager.create_task(prompt=prompt),
                config=retry_config,
                operation_name="创建脚本生成任务",
            )
            
            task_id = task_result.get("task_id") or task_result.get("id")

            if not task_id:
                logger.error(f"[脚本生成] 任务创建失败: 未返回 task_id, 响应: {task_result}")
                raise RuntimeError("Failed to create task: no task_id returned")

            logger.info(f"[脚本生成] 脚本生成任务已创建: task_id={task_id}")

            return {
                "task_id": task_id,
                "prompt": prompt,
            }
            
        except Exception as e:
            logger.error(
                f"[脚本生成] 生成视频制作计划失败: topic={topic}, error={type(e).__name__}: {e}",
                exc_info=True
            )
            raise

    def _build_script_prompt(
        self,
        topic: str,
        duration: int,
        style: str,
        target_audience: str,
    ) -> str:
        """
        构建脚本生成 prompt

        Args:
            topic: 视频主题
            duration: 视频时长（秒）
            style: 视频风格
            target_audience: 目标受众

        Returns:
            完整的 prompt 字符串
        """
        # 根据时长计算建议的场景数量（每个场景约 3-5 秒）
        suggested_scene_count = max(2, min(10, duration // 4))
        
        prompt_parts = [
            f"Generate a comprehensive video production plan for the topic: \"{topic}\"",
            "",
            "=== REQUIREMENTS ===",
            f"1. Video Duration: EXACTLY {duration} seconds (CRITICAL - total scene duration must equal {duration}s)",
            f"2. Video Style: {style} (must be consistently applied throughout)",
            f"3. Target Audience: {target_audience} (content and tone must be appropriate)",
            "",
            "=== OUTPUT FORMAT ===",
            "You MUST output a complete Markdown file with the following EXACT structure:",
            "",
            "```markdown",
            "# Video Production Plan",
            "",
            "## Title",
            "[A concise, engaging title (max 50 characters) that captures the video's essence]",
            "",
            "## Description",
            f"[2-5 sentences describing the video. MUST explicitly mention:",
            f"  - Duration: {duration} seconds",
            f"  - Style: {style}",
            f"  - Target audience: {target_audience}",
            f"  - Overall approach and key message]",
            "",
            "## Script",
            "",
            "### Scene 1 (0:00-0:XX)",
            "**Narration:** \"[Clear, engaging narration text that fits the {target_audience} audience]\"",
            "**Visual:** [Detailed visual description matching {style} style]",
            "**Camera:** [Specific camera movement/angle, e.g., 'Slow zoom in', 'Medium shot', 'Wide establishing shot']",
            "**Duration:** [X seconds - must be precise]",
            "",
            f"### Scene 2 (0:XX-0:YY)",
            "**Narration:** \"[Continuation of the narrative]\"",
            "**Visual:** [Visual description]",
            "**Camera:** [Camera movement]",
            "**Duration:** [X seconds]",
            "",
            f"[Continue with Scene 3, Scene 4, etc. until total duration reaches EXACTLY {duration} seconds]",
            f"[Recommended: {suggested_scene_count} scenes, each approximately {duration // suggested_scene_count} seconds]",
            "",
            "## Storyboard",
            "",
            "### Scene 1 Visual Elements",
            "- **Composition:** [Specific layout and framing description]",
            "- **Color Scheme:** [Detailed color palette matching {style} style]",
            "- **Visual Effects:** [Specific effects to enhance the scene]",
            "- **Design Style:** [Design approach consistent with {style}]",
            "- **Text Overlay:** [Text content if any, or 'None']",
            "- **Animation:** [Animation style and movement description]",
            "",
            "### Scene 2 Visual Elements",
            "[Same structure as Scene 1, matching the Script section]",
            "",
            f"[Continue for all {suggested_scene_count} scenes, ensuring each Storyboard scene matches its Script counterpart]",
            "",
            "## Background Music",
            "",
            "**Style:** [Music style that complements {style} video style]",
            "**Characteristics:**",
            "- Tempo: [Specific BPM value, e.g., 120 BPM]",
            "- Mood: [Mood description appropriate for {target_audience}]",
            "- Instruments: [Specific instrument list]",
            "- Energy Level: [Low/Medium/High - must match video pace]",
            "- Volume: [Volume level, e.g., 'Background level (not overpowering narration)']",
            f"**Duration:** {duration} seconds (MUST match video duration exactly)",
            "**Recommended:** [Specific music type or genre recommendation]",
            "**Notes:** [Additional notes about music integration, if any]",
            "```",
            "",
            "=== CRITICAL REQUIREMENTS ===",
            f"1. DURATION ACCURACY:",
            f"   - Sum of all scene durations MUST equal EXACTLY {duration} seconds",
            f"   - Background Music Duration MUST be EXACTLY {duration} seconds",
            f"   - Use precise time ranges (e.g., 0:00-0:15, 0:15-0:30)",
            "",
            f"2. STYLE CONSISTENCY:",
            f"   - Video style MUST be: {style}",
            f"   - Apply {style} style consistently across all scenes",
            f"   - Description, Script, Storyboard, and Music must all reflect {style}",
            "",
            f"3. AUDIENCE ALIGNMENT:",
            f"   - Content MUST be appropriate for: {target_audience}",
            f"   - Narration tone and language must match {target_audience} expectations",
            "",
            "4. FORMAT COMPLIANCE:",
            "   - Scene numbers MUST be consecutive (Scene 1, Scene 2, Scene 3, ...)",
            "   - Storyboard section MUST have the same number of scenes as Script section",
            "   - Each scene MUST have all required fields (Narration, Visual, Camera, Duration)",
            "   - Time ranges MUST be in MM:SS format (e.g., 0:00-0:15, 1:30-2:00)",
            "",
            "5. QUALITY STANDARDS:",
            "   - Narration should be clear, engaging, and natural",
            "   - Visual descriptions should be specific and detailed",
            "   - Storyboard elements should be production-ready",
            "   - Music recommendations should be specific and actionable",
            "",
            "=== OUTPUT INSTRUCTIONS ===",
            "Generate the complete Markdown file following the format above.",
            "Ensure all sections are present, properly formatted, and meet all requirements.",
            "The output should be ready for direct use in video production.",
        ]

        return "\n".join(prompt_parts)

    async def _extract_markdown(
        self,
        task_result: Dict[str, Any],
    ) -> str:
        """
        从任务结果提取 Markdown 内容

        Args:
            task_result: Manus API 返回的任务结果

        Returns:
            Markdown 内容字符串
        """
        logger.info("[脚本生成] 提取 Markdown 内容...")

        # Manus API 返回的结构：output 字段包含消息列表
        outputs = task_result.get("output", task_result.get("outputs", []))

        markdown_content = None
        markdown_file_url = None

        # 遍历 output 消息，查找文本类型或文件类型的输出
        for output in outputs:
            content = output.get("content", [])
            for item in content:
                item_type = item.get("type", "")
                
                # 1. 查找 output_text 类型的内容（可能包含 Markdown）
                if item_type == "text" or item_type == "output_text":
                    text = item.get("text", "")
                    # 检查是否包含 Markdown 格式（包含 # Video Production Plan）
                    if "# Video Production Plan" in text or "## Title" in text:
                        markdown_content = text
                        logger.info("[脚本生成] 从 output_text 中找到 Markdown 内容")
                        break
                
                # 2. 查找 output_file 类型的内容（Markdown 文件）
                elif item_type == "output_file":
                    file_url = item.get("fileUrl") or item.get("file_url")
                    file_name = item.get("fileName") or item.get("file_name")
                    mime_type = item.get("mimeType") or item.get("mime_type")
                    
                    # 检查是否是 Markdown 文件
                    if file_name and (file_name.endswith(".md") or mime_type == "text/markdown"):
                        markdown_file_url = file_url
                        logger.info(f"[脚本生成] 找到 Markdown 文件: {file_name}, URL: {file_url[:80]}...")
                        break
                
                # 3. 也检查其他可能的字段
                elif "markdown" in item_type.lower() or "plan" in item_type.lower():
                    markdown_content = item.get("text", item.get("content", ""))
                    if markdown_content:
                        logger.info("[脚本生成] 从其他字段中找到 Markdown 内容")
                        break

            if markdown_content or markdown_file_url:
                break

        # 如果没有找到文本内容，但有文件 URL，则下载文件
        if not markdown_content and markdown_file_url:
            logger.info(f"[脚本生成] 从文件 URL 下载 Markdown 内容: {markdown_file_url[:80]}...")
            try:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    response = await client.get(markdown_file_url)
                    response.raise_for_status()
                    markdown_content = response.text
                    logger.info(f"[脚本生成] Markdown 文件下载成功，长度: {len(markdown_content)} 字符")
            except Exception as e:
                logger.error(f"[脚本生成] 下载 Markdown 文件失败: {e}", exc_info=True)
                raise RuntimeError(f"下载 Markdown 文件失败: {e}") from e

        # 如果还没有找到，尝试从整个 output 中提取（作为后备方案）
        if not markdown_content:
            logger.debug("[脚本生成] 尝试从整个 output 中提取 Markdown...")
            import json
            output_str = json.dumps(outputs, indent=2, ensure_ascii=False)
            # 查找 Markdown 代码块
            markdown_match = re.search(
                r"```(?:markdown)?\s*(# Video Production Plan.*?)```",
                output_str,
                re.DOTALL,
            )
            if markdown_match:
                markdown_content = markdown_match.group(1).strip()
                logger.info("[脚本生成] 从 JSON 字符串中提取到 Markdown 内容")

        if not markdown_content:
            logger.error(f"[脚本生成] 无法从任务结果中提取 Markdown")
            logger.debug(f"[脚本生成] 任务结果结构: output 消息数={len(outputs)}")
            for i, output in enumerate(outputs):
                logger.debug(f"[脚本生成] Output[{i}]: role={output.get('role')}, type={output.get('type')}, content_types={[item.get('type') for item in output.get('content', [])]}")
            raise RuntimeError(
                "Failed to extract Markdown from task result. "
                "Check logs for task details."
            )

        logger.info(f"[脚本生成] 成功提取 Markdown，长度: {len(markdown_content)} 字符")

        return markdown_content

    async def _save_markdown(
        self,
        markdown_content: str,
        task_id: str,
    ) -> Path:
        """
        保存 Markdown 文件

        Args:
            markdown_content: Markdown 内容
            task_id: 任务 ID（用于生成文件名）

        Returns:
            保存的文件路径
        """
        # 生成唯一文件名（基于 task_id）
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"video_plan_{task_id[:8]}_{timestamp}.md"
        file_path = self.settings.markdown_storage_dir / filename

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存文件
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(markdown_content)

        logger.info(f"Markdown 文件已保存: {file_path}")

        return file_path

    async def _read_markdown(
        self,
        file_path: Path,
    ) -> str:
        """
        读取 Markdown 文件

        Args:
            file_path: Markdown 文件路径

        Returns:
            Markdown 内容字符串

        Raises:
            FileNotFoundError: 文件不存在
            IOError: 文件读取失败
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Markdown 文件不存在: {file_path}")

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            logger.info(f"Markdown 文件已读取: {file_path} (长度: {len(content)} 字符)")

            return content

        except Exception as e:
            logger.error(f"读取 Markdown 文件失败: {file_path}, 错误: {e}")
            raise IOError(f"读取 Markdown 文件失败: {e}") from e

    async def _read_markdown_by_task_id(
        self,
        task_id: str,
    ) -> Optional[str]:
        """
        根据任务 ID 读取 Markdown 文件

        会在存储目录中查找包含该 task_id 的文件

        Args:
            task_id: 任务 ID

        Returns:
            Markdown 内容字符串，如果文件不存在则返回 None
        """
        storage_dir = self.settings.markdown_storage_dir

        if not storage_dir.exists():
            logger.warning(f"存储目录不存在: {storage_dir}")
            return None

        # 查找包含 task_id 的文件
        task_id_prefix = task_id[:8]
        pattern = f"video_plan_{task_id_prefix}_*.md"

        import glob
        matching_files = list(storage_dir.glob(pattern))

        if not matching_files:
            logger.warning(f"未找到任务 {task_id} 的 Markdown 文件")
            return None

        # 如果有多个文件，选择最新的（按文件名排序）
        matching_files.sort(reverse=True)
        latest_file = matching_files[0]

        try:
            return await self._read_markdown(latest_file)
        except Exception as e:
            logger.error(f"读取任务 {task_id} 的 Markdown 文件失败: {e}")
            return None

    async def _validate_markdown(
        self,
        markdown_content: str,
        duration: int,
        style: str,
    ) -> Dict[str, Any]:
        """
        验证 Markdown 格式（使用 MarkdownValidator）

        Args:
            markdown_content: Markdown 内容
            duration: 期望的视频时长（秒）
            style: 期望的视频风格

        Returns:
            验证结果字典，包含 is_valid, errors, warnings, parsed_plan
        """
        return MarkdownValidator.validate(markdown_content, duration, style)
