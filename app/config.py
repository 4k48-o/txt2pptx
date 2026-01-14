"""
Application Configuration - 应用配置管理
"""

import os
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

    # 存储配置
    output_dir: Path = Field(default=Path("./storage/output"), env="OUTPUT_DIR")
    tasks_file: Path = Field(default=Path("./storage/tasks.json"), env="TASKS_FILE")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 服务配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")

    # CORS 配置
    cors_origins: list[str] = Field(
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


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()

