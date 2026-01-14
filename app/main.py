"""
FastAPI Application Entry Point - 应用入口
"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import get_settings
from .api.router import api_router
from .api.websocket import router as websocket_router
from .exceptions import setup_exception_handlers
from .dependencies import cleanup_manus_client

# 配置日志
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting Manus PPT Generator API...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Output directory: {settings.output_dir}")
    
    if not settings.manus_api_key:
        logger.warning("MANUS_API_KEY not configured!")
    
    yield
    
    # 关闭时
    logger.info("Shutting down Manus PPT Generator API...")
    await cleanup_manus_client()
    logger.info("Cleaned up Manus client connection")


# 创建 FastAPI 应用
app = FastAPI(
    title="Manus PPT Generator API",
    description="自动化 PPT 生成服务，基于 Manus AI",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理
setup_exception_handlers(app)

# 注册路由
app.include_router(api_router)

# 注册 WebSocket 路由
app.include_router(websocket_router)

# 静态文件目录
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# 根路径 - 返回前端页面
@app.get("/")
async def root():
    """根路径，返回前端页面"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Manus PPT Generator API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# 挂载静态文件（放在最后，避免覆盖其他路由）
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

