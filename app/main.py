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
from .api.webhook import router as webhook_router
from .exceptions import setup_exception_handlers
from .dependencies import cleanup_manus_client, get_manus_client
from .manus_client import register_webhook_on_startup, unregister_webhook_on_shutdown

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
    
    # 如果启用了 Webhook，自动注册
    manus_client = None
    if settings.webhook_enabled:
        logger.info("Webhook 已启用，准备注册...")
        if settings.webhook_base_url:
            from .manus_client import AsyncManusClient
            manus_client = AsyncManusClient()
            webhook_id = await register_webhook_on_startup(manus_client)
            if webhook_id:
                logger.info(f"Webhook 注册成功: {settings.webhook_base_url}{settings.webhook_path}")
            else:
                logger.warning("Webhook 注册失败")
        else:
            logger.warning("WEBHOOK_BASE_URL 未配置，跳过 Webhook 注册")
    
    yield
    
    # 关闭时
    logger.info("Shutting down Manus PPT Generator API...")
    
    # 注销 Webhook
    if manus_client and settings.webhook_enabled:
        await unregister_webhook_on_shutdown(manus_client)
        await manus_client.close()
    
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

# 注册 Webhook 路由
app.include_router(webhook_router)

# 静态文件目录
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# 根路径 - 返回前端页面
@app.get("/")
async def root():
    """根路径，返回前端页面（轮询模式）"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Manus PPT Generator API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/realtime")
async def realtime_page():
    """实时模式页面（WebSocket + Webhook）"""
    webhook_file = STATIC_DIR / "webhook.html"
    if webhook_file.exists():
        return FileResponse(webhook_file)
    return {"error": "webhook.html not found"}


# 挂载静态文件（放在最后，避免覆盖其他路由）
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

