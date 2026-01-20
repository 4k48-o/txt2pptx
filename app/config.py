"""
Application Configuration - 应用配置管理
"""

import os
from typing import List
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""

    # Manus API
    manus_api_key: str = Field(default="", env="MANUS_API_KEY")
    manus_api_base_url: str = Field(
        default="https://api.manus.ai", env="MANUS_API_BASE_URL"
    )

    # 轮询配置
    poll_interval: int = Field(default=5, env="POLL_INTERVAL")
    poll_timeout: int = Field(default=600, env="POLL_TIMEOUT")

    # Webhook 配置
    webhook_enabled: bool = Field(default=False, env="WEBHOOK_ENABLED")
    webhook_base_url: str = Field(default="", env="WEBHOOK_BASE_URL")
    webhook_path: str = Field(default="/webhook/manus", env="WEBHOOK_PATH")

    # 存储配置
    output_dir: Path = Field(default=Path("./storage/output"), env="OUTPUT_DIR")
    tasks_file: Path = Field(default=Path("./storage/tasks.json"), env="TASKS_FILE")
    
    # 视频生成配置
    video_storage_dir: Path = Field(
        default=Path("./storage/videos"), env="VIDEO_STORAGE_DIR"
    )
    markdown_storage_dir: Path = Field(
        default=Path("./storage/markdown"), env="MARKDOWN_STORAGE_DIR"
    )
    video_min_duration: int = Field(default=5, env="VIDEO_MIN_DURATION")
    video_max_duration: int = Field(default=30, env="VIDEO_MAX_DURATION")
    # 注意：List 类型的环境变量需要使用 JSON 格式或逗号分隔的字符串
    # 这里使用默认值，如需从环境变量读取，请使用 JSON 格式
    video_supported_durations: List[int] = Field(
        default=[5, 10, 15, 20, 25, 30],
        description="支持的视频时长列表（秒）",
    )
    video_supported_styles: List[str] = Field(
        default=["educational", "promotional", "documentary", "tutorial", "corporate"],
        description="支持的视频风格列表",
    )
    video_supported_audiences: List[str] = Field(
        default=["general", "students", "professionals", "executives"],
        description="支持的目标受众列表",
    )
    video_supported_formats: List[str] = Field(
        default=["mp4"],
        description="支持的视频格式列表",
    )

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 服务配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")

    # CORS 配置
    cors_origins: List[str] = Field(
        default=["*"],
        env="CORS_ORIGINS",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self.video_storage_dir.mkdir(parents=True, exist_ok=True)
        self.markdown_storage_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()

