"""
PPT Generator Service - PPT 生成服务
"""

import os
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..manus_client import ManusClient, TaskManager, FileManager
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PPTGenerator:
    """PPT 生成服务"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 PPT 生成器

        Args:
            api_key: Manus API Key，如果不传则从环境变量读取
        """
        self.client = ManusClient(api_key=api_key)
        self.task_manager = TaskManager(self.client)
        self.file_manager = FileManager(self.client)
        self.config = Config()

        logger.info("PPT Generator initialized")

    def generate(
        self,
        topic: str,
        audience: Optional[str] = None,
        slides_count: Optional[int] = None,
        style: Optional[str] = None,
        reference_files: Optional[List[str]] = None,
        output_filename: Optional[str] = None,
    ) -> Path:
        """
        生成 PPT

        Args:
            topic: PPT 主题
            audience: 目标受众
            slides_count: 页数
            style: 风格描述
            reference_files: 参考文件路径列表
            output_filename: 输出文件名，不传则自动生成

        Returns:
            生成的 PPT 文件路径
        """
        logger.info(f"Generating PPT for topic: {topic}")

        # 1. 上传参考文件（如果有）
        attachments = []
        if reference_files:
            attachments = self._upload_reference_files(reference_files)

        # 2. 构建 Prompt
        prompt = self._build_prompt(topic, audience, slides_count, style)

        # 3. 创建任务
        task = self.task_manager.create_task(prompt=prompt, attachments=attachments)
        task_id = task.get("task_id")

        if not task_id:
            raise RuntimeError("Failed to create task: no task_id returned")

        # 4. 等待任务完成
        completed_task = self.task_manager.wait_for_completion(task_id)

        # 5. 下载结果
        output_path = self._download_result(completed_task, output_filename)

        logger.info(f"PPT generated successfully: {output_path}")

        return output_path

    def _upload_reference_files(self, file_paths: List[str]) -> List[Dict[str, str]]:
        """上传参考文件"""
        attachments = []

        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"Reference file not found, skipping: {file_path}")
                continue

            result = self.file_manager.upload_file(file_path)
            attachments.append({
                "filename": result["filename"],
                "file_id": result["file_id"],
            })

        return attachments

    def _build_prompt(
        self,
        topic: str,
        audience: Optional[str] = None,
        slides_count: Optional[int] = None,
        style: Optional[str] = None,
    ) -> str:
        """构建 Prompt"""
        prompt_parts = [f"生成一份 PPT，主题为 \"{topic}\""]

        if audience:
            prompt_parts.append(f"目标受众：{audience}")

        prompt_parts.append("要求：")

        if slides_count:
            prompt_parts.append(f"- 页数：约 {slides_count} 页")
        else:
            prompt_parts.append("- 页数：根据内容自动确定")

        prompt_parts.append("- 每页包含标题、要点、图表（如适用）")
        prompt_parts.append("- 如果已有参考文件作为输入，请整合其关键内容")
        prompt_parts.append("- 如果有包含具体数据不要捏造，并给出数据的来源网站")
        

        if style:
            prompt_parts.append(f"- 风格：{style}")

        prompt_parts.append("- 导出格式：PPTX")

        return "\n".join(prompt_parts)

    def _download_result(
        self,
        task: Dict[str, Any],
        output_filename: Optional[str] = None,
    ) -> Path:
        """下载生成的 PPT"""
        # 从任务结果中获取下载链接
        # API 返回的结构使用 "output" 而不是 "outputs"
        outputs = task.get("output", task.get("outputs", []))

        pptx_url = None
        file_name = None
        
        # 遍历 output 消息，查找文件类型的输出
        for output in outputs:
            # 检查消息内容
            content = output.get("content", [])
            for item in content:
                item_type = item.get("type", "")
                # 查找 output_file 类型（Manus 返回的格式）
                if item_type == "output_file":
                    # 字段名是 fileUrl 而不是 url
                    url = item.get("fileUrl", item.get("url", item.get("file_url", "")))
                    file_name = item.get("fileName", item.get("filename", ""))
                    if url:
                        pptx_url = url
                        break
                # 也检查其他文件类型
                elif item_type in ["file", "artifact"]:
                    url = item.get("fileUrl", item.get("url", ""))
                    if url:
                        pptx_url = url
                        break
            if pptx_url:
                break

        if not pptx_url:
            # 尝试从其他字段获取
            pptx_url = task.get("output_url") or task.get("result_url") or task.get("download_url")

        if not pptx_url:
            # 打印任务详情以便调试
            logger.error(f"Task result: {task}")
            raise RuntimeError("No PPTX download URL found in task result. Check logs for task details.")

        # 确定输出文件名
        if not output_filename:
            # 优先使用 API 返回的文件名
            if file_name:
                output_filename = f"{file_name}.pptx"
            else:
                # 使用任务 ID
                task_id = task.get("id", task.get("task_id", "unknown"))
                output_filename = f"ppt_{task_id}.pptx"

        if not output_filename.endswith(".pptx"):
            output_filename += ".pptx"

        output_path = self.config.output_dir / output_filename

        # 下载文件
        logger.info(f"Downloading PPT from: {pptx_url[:80]}...")
        logger.info(f"Saving to: {output_path}")

        response = requests.get(pptx_url)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Downloaded {len(response.content)} bytes")

        return output_path

