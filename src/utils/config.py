"""
Configuration Management - 配置管理
"""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """配置管理类"""

    _instance = None
    _loaded = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置"""
        if not Config._loaded:
            self._load_env()
            Config._loaded = True

    def _load_env(self):
        """加载环境变量"""
        # 尝试从项目根目录加载 .env 文件
        # __file__ = src/utils/config.py
        # parent = src/utils/
        # parent.parent = src/
        # parent.parent.parent = 项目根目录
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    @property
    def manus_api_key(self) -> str:
        """Manus API Key"""
        return os.getenv("MANUS_API_KEY", "")

    @property
    def manus_api_base_url(self) -> str:
        """Manus API Base URL"""
        return os.getenv("MANUS_API_BASE_URL", "https://api.manus.ai")

    @property
    def poll_interval(self) -> int:
        """轮询间隔（秒）"""
        return int(os.getenv("POLL_INTERVAL", "5"))

    @property
    def poll_timeout(self) -> int:
        """轮询超时时间（秒）"""
        return int(os.getenv("POLL_TIMEOUT", "600"))

    @property
    def output_dir(self) -> Path:
        """输出目录"""
        output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @property
    def log_level(self) -> str:
        """日志级别"""
        return os.getenv("LOG_LEVEL", "INFO").upper()

