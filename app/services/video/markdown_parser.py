"""
Markdown Parser and Validator - Markdown 解析器和验证器

用于解析和验证视频制作计划的 Markdown 文件
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """场景数据结构"""

    number: int
    time_range: str  # 例如: "0:00-0:15"
    narration: str
    visual: str
    camera: Optional[str] = None
    duration: Optional[int] = None  # 秒数


@dataclass
class StoryboardElement:
    """分镜元素数据结构"""

    scene_number: int
    composition: Optional[str] = None
    color_scheme: Optional[str] = None
    visual_effects: Optional[str] = None
    design_style: Optional[str] = None
    text_overlay: Optional[str] = None
    animation: Optional[str] = None


@dataclass
class BackgroundMusic:
    """背景音乐数据结构"""

    style: Optional[str] = None
    tempo: Optional[str] = None
    mood: Optional[str] = None
    instruments: Optional[str] = None
    energy_level: Optional[str] = None
    volume: Optional[str] = None
    duration: Optional[int] = None  # 秒数
    recommended: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class VideoPlan:
    """视频制作计划数据结构"""

    title: Optional[str] = None
    description: Optional[str] = None
    scenes: List[Scene] = field(default_factory=list)
    storyboard: List[StoryboardElement] = field(default_factory=list)
    background_music: Optional[BackgroundMusic] = None


class MarkdownParser:
    """Markdown 解析器"""

    @staticmethod
    def parse(markdown_content: str) -> VideoPlan:
        """
        解析 Markdown 内容

        Args:
            markdown_content: Markdown 内容字符串

        Returns:
            VideoPlan 对象
        """
        plan = VideoPlan()

        # 解析 Title
        plan.title = MarkdownParser._parse_title(markdown_content)

        # 解析 Description
        plan.description = MarkdownParser._parse_description(markdown_content)

        # 解析 Script 部分
        plan.scenes = MarkdownParser._parse_script(markdown_content)

        # 解析 Storyboard 部分
        plan.storyboard = MarkdownParser._parse_storyboard(markdown_content)

        # 解析 Background Music 部分
        plan.background_music = MarkdownParser._parse_background_music(markdown_content)

        return plan

    @staticmethod
    def _parse_title(markdown_content: str) -> Optional[str]:
        """解析 Title 部分"""
        pattern = r"##\s*Title\s*\n(.+?)(?=\n##|\Z)"
        match = re.search(pattern, markdown_content, re.MULTILINE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            # 移除可能的 Markdown 格式标记
            title = re.sub(r"^\*\*|\*\*$", "", title)
            return title
        return None

    @staticmethod
    def _parse_description(markdown_content: str) -> Optional[str]:
        """解析 Description 部分"""
        pattern = r"##\s*Description\s*\n(.+?)(?=\n##|\Z)"
        match = re.search(pattern, markdown_content, re.MULTILINE | re.DOTALL)
        if match:
            description = match.group(1).strip()
            # 移除可能的 Markdown 格式标记
            description = re.sub(r"\*\*Note:\*\*.*", "", description, flags=re.IGNORECASE)
            return description.strip()
        return None

    @staticmethod
    def _parse_script(markdown_content: str) -> List[Scene]:
        """解析 Script 部分，提取所有场景"""
        scenes = []

        # 提取 Script 部分
        script_pattern = r"##\s*Script\s*\n(.*?)(?=\n##|\Z)"
        script_match = re.search(script_pattern, markdown_content, re.MULTILINE | re.DOTALL)
        if not script_match:
            return scenes

        script_content = script_match.group(1)

        # 匹配每个场景
        scene_pattern = r"###\s*Scene\s*(\d+)\s*\(([\d:]+)-([\d:]+)\)\s*\n(.*?)(?=\n###|\Z)"
        scene_matches = re.finditer(scene_pattern, script_content, re.MULTILINE | re.DOTALL)

        for match in scene_matches:
            scene_num = int(match.group(1))
            start_time = match.group(2)
            end_time = match.group(3)
            scene_content = match.group(4)

            # 解析场景内容
            narration_match = re.search(
                r"\*\*Narration:\*\*\s*\"([^\"]+)\"", scene_content, re.IGNORECASE
            )
            visual_match = re.search(
                r"\*\*Visual:\*\*\s*(.+?)(?=\n\*\*|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            camera_match = re.search(
                r"\*\*Camera:\*\*\s*(.+?)(?=\n\*\*|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            duration_match = re.search(
                r"\*\*Duration:\*\*\s*(\d+)\s*seconds?", scene_content, re.IGNORECASE
            )

            scene = Scene(
                number=scene_num,
                time_range=f"{start_time}-{end_time}",
                narration=narration_match.group(1) if narration_match else "",
                visual=visual_match.group(1).strip() if visual_match else "",
                camera=camera_match.group(1).strip() if camera_match else None,
                duration=int(duration_match.group(1)) if duration_match else None,
            )

            scenes.append(scene)

        return scenes

    @staticmethod
    def _parse_storyboard(markdown_content: str) -> List[StoryboardElement]:
        """解析 Storyboard 部分，提取视觉元素"""
        elements = []

        # 提取 Storyboard 部分
        storyboard_pattern = r"##\s*Storyboard\s*\n(.*?)(?=\n##|\Z)"
        storyboard_match = re.search(
            storyboard_pattern, markdown_content, re.MULTILINE | re.DOTALL
        )
        if not storyboard_match:
            return elements

        storyboard_content = storyboard_match.group(1)

        # 匹配每个场景的视觉元素
        scene_pattern = r"###\s*Scene\s*(\d+)\s*Visual\s*Elements\s*\n(.*?)(?=\n###|\Z)"
        scene_matches = re.finditer(scene_pattern, storyboard_content, re.MULTILINE | re.DOTALL)

        for match in scene_matches:
            scene_num = int(match.group(1))
            scene_content = match.group(2)

            # 解析各个字段
            composition_match = re.search(
                r"\*\*Composition:\*\*\s*(.+?)(?=\n-|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            color_match = re.search(
                r"\*\*Color\s*Scheme:\*\*\s*(.+?)(?=\n-|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            effects_match = re.search(
                r"\*\*Visual\s*Effects:\*\*\s*(.+?)(?=\n-|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            design_match = re.search(
                r"\*\*Design\s*Style:\*\*\s*(.+?)(?=\n-|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            text_match = re.search(
                r"\*\*Text\s*Overlay:\*\*\s*(.+?)(?=\n-|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )
            animation_match = re.search(
                r"\*\*Animation:\*\*\s*(.+?)(?=\n-|\Z)", scene_content, re.IGNORECASE | re.DOTALL
            )

            element = StoryboardElement(
                scene_number=scene_num,
                composition=composition_match.group(1).strip() if composition_match else None,
                color_scheme=color_match.group(1).strip() if color_match else None,
                visual_effects=effects_match.group(1).strip() if effects_match else None,
                design_style=design_match.group(1).strip() if design_match else None,
                text_overlay=text_match.group(1).strip() if text_match else None,
                animation=animation_match.group(1).strip() if animation_match else None,
            )

            elements.append(element)

        return elements

    @staticmethod
    def _parse_background_music(markdown_content: str) -> Optional[BackgroundMusic]:
        """解析 Background Music 部分"""
        # 提取 Background Music 部分
        music_pattern = r"##\s*Background\s*Music\s*\n(.*?)(?=\n##|\Z)"
        music_match = re.search(music_pattern, markdown_content, re.MULTILINE | re.DOTALL)
        if not music_match:
            return None

        music_content = music_match.group(1)

        # 解析各个字段
        style_match = re.search(
            r"\*\*Style:\*\*\s*(.+?)(?=\n\*\*|\Z)", music_content, re.IGNORECASE | re.DOTALL
        )
        tempo_match = re.search(
            r"Tempo:\s*([^\n]+)", music_content, re.IGNORECASE
        )
        mood_match = re.search(
            r"Mood:\s*([^\n]+)", music_content, re.IGNORECASE
        )
        instruments_match = re.search(
            r"Instruments:\s*([^\n]+)", music_content, re.IGNORECASE
        )
        energy_match = re.search(
            r"Energy\s*Level:\s*([^\n]+)", music_content, re.IGNORECASE
        )
        volume_match = re.search(
            r"Volume:\s*([^\n]+)", music_content, re.IGNORECASE
        )
        duration_match = re.search(
            r"\*\*Duration:\*\*\s*(\d+)\s*seconds?", music_content, re.IGNORECASE
        )
        recommended_match = re.search(
            r"\*\*Recommended:\*\*\s*(.+?)(?=\n\*\*|\Z)", music_content, re.IGNORECASE | re.DOTALL
        )
        notes_match = re.search(
            r"\*\*Notes:\*\*\s*(.+?)(?=\n\*\*|\Z)", music_content, re.IGNORECASE | re.DOTALL
        )

        return BackgroundMusic(
            style=style_match.group(1).strip() if style_match else None,
            tempo=tempo_match.group(1).strip() if tempo_match else None,
            mood=mood_match.group(1).strip() if mood_match else None,
            instruments=instruments_match.group(1).strip() if instruments_match else None,
            energy_level=energy_match.group(1).strip() if energy_match else None,
            volume=volume_match.group(1).strip() if volume_match else None,
            duration=int(duration_match.group(1)) if duration_match else None,
            recommended=recommended_match.group(1).strip() if recommended_match else None,
            notes=notes_match.group(1).strip() if notes_match else None,
        )


class MarkdownValidator:
    """Markdown 验证器"""

    @staticmethod
    def validate(
        markdown_content: str,
        duration: int,
        style: str,
    ) -> Dict[str, Any]:
        """
        验证 Markdown 格式

        Args:
            markdown_content: Markdown 内容
            duration: 期望的视频时长（秒）
            style: 期望的视频风格

        Returns:
            验证结果字典，包含 is_valid, errors, warnings, parsed_plan
        """
        errors = []
        warnings = []

        # 先解析 Markdown
        try:
            parsed_plan = MarkdownParser.parse(markdown_content)
        except Exception as e:
            logger.error(f"解析 Markdown 失败: {e}", exc_info=True)
            errors.append(f"Markdown 解析失败: {str(e)}")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "parsed_plan": None,
            }

        # 1. 验证必需部分是否存在
        if not parsed_plan.title:
            errors.append("缺少必需部分: ## Title")
        if not parsed_plan.description:
            errors.append("缺少必需部分: ## Description")
        if not parsed_plan.scenes:
            errors.append("缺少必需部分: ## Script (无场景)")
        if not parsed_plan.storyboard:
            errors.append("缺少必需部分: ## Storyboard")
        if not parsed_plan.background_music:
            errors.append("缺少必需部分: ## Background Music")

        # 2. 验证场景数量与时长匹配
        if parsed_plan.scenes:
            total_duration = sum(
                scene.duration for scene in parsed_plan.scenes if scene.duration
            )
            # 允许 ±1 秒误差
            if abs(total_duration - duration) > 1:
                errors.append(
                    f"场景总时长 ({total_duration}s) 与期望时长 ({duration}s) 不匹配"
                )
            elif total_duration != duration:
                warnings.append(
                    f"场景总时长 ({total_duration}s) 与期望时长 ({duration}s) 有轻微差异"
                )

        # 3. 验证 Background Music 的 Duration
        if parsed_plan.background_music and parsed_plan.background_music.duration:
            music_duration = parsed_plan.background_music.duration
            if abs(music_duration - duration) > 1:
                errors.append(
                    f"背景音乐时长 ({music_duration}s) 与期望时长 ({duration}s) 不匹配"
                )
            elif music_duration != duration:
                warnings.append(
                    f"背景音乐时长 ({music_duration}s) 与期望时长 ({duration}s) 有轻微差异"
                )

        # 4. 验证风格描述
        if parsed_plan.description:
            description_lower = parsed_plan.description.lower()
            style_lower = style.lower()
            if style_lower not in description_lower:
                warnings.append(
                    f"Description 部分可能未明确提及风格 '{style}'"
                )

        # 5. 验证场景编号连续性
        if parsed_plan.scenes:
            scene_numbers = [scene.number for scene in parsed_plan.scenes]
            expected_numbers = list(range(1, len(scene_numbers) + 1))
            if scene_numbers != expected_numbers:
                errors.append(
                    f"场景编号不连续: 期望 {expected_numbers}, 实际 {scene_numbers}"
                )

        # 6. 验证时间格式
        if parsed_plan.scenes:
            for scene in parsed_plan.scenes:
                time_range = scene.time_range
                # 验证时间格式 MM:SS-MM:SS
                if not re.match(r"^\d+:\d{2}-\d+:\d{2}$", time_range):
                    errors.append(
                        f"场景 {scene.number} 时间格式错误: {time_range} (应为 MM:SS-MM:SS)"
                    )
                else:
                    # 验证时间范围合理性
                    try:
                        start_str, end_str = time_range.split("-")
                        start_parts = start_str.split(":")
                        end_parts = end_str.split(":")
                        start_total = int(start_parts[0]) * 60 + int(start_parts[1])
                        end_total = int(end_parts[0]) * 60 + int(end_parts[1])

                        if end_total <= start_total:
                            errors.append(
                                f"场景 {scene.number} 时间范围错误: {time_range} (结束时间必须大于开始时间)"
                            )
                    except (ValueError, IndexError):
                        errors.append(
                            f"场景 {scene.number} 时间范围解析失败: {time_range}"
                        )

        # 7. 验证 Storyboard 与 Script 场景数量匹配
        if parsed_plan.scenes and parsed_plan.storyboard:
            script_scene_count = len(parsed_plan.scenes)
            storyboard_scene_count = len(parsed_plan.storyboard)
            if script_scene_count != storyboard_scene_count:
                errors.append(
                    f"Storyboard 场景数量 ({storyboard_scene_count}) 与 Script 场景数量 ({script_scene_count}) 不匹配"
                )

        # 8. 验证每个场景的必需字段
        for scene in parsed_plan.scenes:
            if not scene.narration:
                warnings.append(f"场景 {scene.number} 缺少 Narration")
            if not scene.visual:
                warnings.append(f"场景 {scene.number} 缺少 Visual")
            if not scene.duration:
                warnings.append(f"场景 {scene.number} 缺少 Duration")

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "parsed_plan": parsed_plan,
        }
