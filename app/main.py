"""
FastAPI Application Entry Point - 应用入口
"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

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
            if webhook_id is not None:
                # webhook_id 可能为空字符串（表示已存在但无法获取 id）或实际的 webhook_id
                if webhook_id:
                    logger.info(f"Webhook 注册成功: {settings.webhook_callback_url()}, webhook_id={webhook_id}")
                else:
                    logger.info(f"Webhook 已存在: {settings.webhook_callback_url()}")
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


# ========== 业务子应用（最终对外挂载到 /manus） ==========
manus_app = FastAPI(
    title="Manus PPT Generator API",
    description="自动化 PPT 生成服务，基于 Manus AI",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
manus_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理
setup_exception_handlers(manus_app)

# 静态文件目录
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# 根路径 - 返回服务选择页面或重定向（必须在其他路由之前注册，确保优先级）
@manus_app.get("/")
async def root():
    """根路径，返回服务选择页面"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Manus Multi-Service API",
        "version": "0.3.0",
        "services": {
            "ppt": "/manus/ppt",
            "video": "/manus/video",
            "crawler": "/manus/crawler",
        },
        "docs": "/manus/docs",
        "health": "/manus/api/health",
    }

# 注册路由（在根路径之后注册，避免覆盖）
manus_app.include_router(api_router)

# 注册 WebSocket 路由
manus_app.include_router(websocket_router)

# Webhook 路由：根据 webhook_path 配置决定注册位置
# 如果 webhook_path 以 /manus 开头，则在 manus_app 上注册（路径：/manus/webhook/manus）
# 否则在根应用上注册（路径：/webhook/manus）
# 注意：webhook_path 配置应该与路由注册位置匹配
webhook_path = settings.normalized_webhook_path()
if webhook_path.startswith("/manus"):
    # webhook_path 包含 /manus，在 manus_app 上注册
    manus_app.include_router(webhook_router)
    logger.info(f"Webhook 路由注册在 manus_app 上，完整路径: /manus{webhook_path}")
else:
    # webhook_path 不包含 /manus，稍后在根应用上注册
    logger.info(f"Webhook 路由将在 root_app 上注册，完整路径: {webhook_path}")


# ========== 服务页面路由 ==========

@manus_app.get("/ppt")
async def ppt_page():
    """PPT 生成服务页面"""
    ppt_file = STATIC_DIR / "ppt" / "index.html"
    if ppt_file.exists():
        return FileResponse(ppt_file)
    # 向后兼容：尝试旧路径
    fallback_file = STATIC_DIR / "index.html"
    if fallback_file.exists():
        return FileResponse(fallback_file)
    return {"error": "PPT service page not found"}


@manus_app.get("/video")
async def video_page():
    """视频生成服务页面"""
    video_file = STATIC_DIR / "video" / "index.html"
    if video_file.exists():
        return FileResponse(video_file)
    # 向后兼容：尝试旧路径
    fallback_file = STATIC_DIR / "video.html"
    if fallback_file.exists():
        return FileResponse(fallback_file)
    return {"error": "Video service page not found"}


@manus_app.get("/crawler")
async def crawler_page():
    """爬虫服务页面"""
    crawler_file = STATIC_DIR / "crawler" / "index.html"
    if crawler_file.exists():
        return FileResponse(crawler_file)
    return {"error": "Crawler service page not found"}


# ========== 向后兼容的旧路由（标记为废弃） ==========

@manus_app.get("/realtime")
async def realtime_page():
    """实时模式页面（WebSocket + Webhook）- 已废弃，请使用 /ppt"""
    webhook_file = STATIC_DIR / "webhook.html"
    if webhook_file.exists():
        return FileResponse(webhook_file)
    return {"error": "webhook.html not found", "deprecated": True, "use": "/manus/ppt"}


@manus_app.get("/tasks")
async def tasks_page():
    """任务列表页面 - 已废弃，请使用 /ppt"""
    tasks_file = STATIC_DIR / "tasks.html"
    if tasks_file.exists():
        return FileResponse(tasks_file)
    return {"error": "tasks.html not found", "deprecated": True, "use": "/manus/ppt"}


# 挂载静态文件（放在最后，避免覆盖其他路由）
if STATIC_DIR.exists():
    manus_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Favicon 路由（避免 404 错误）
@manus_app.get("/favicon.ico")
async def favicon():
    """返回 favicon，使用 logo 作为图标"""
    favicon_path = STATIC_DIR / "logo" / "logo.png"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/png")
    # 如果不存在，返回 204 No Content
    from fastapi.responses import Response
    return Response(status_code=204)


# ========== 根应用（只负责挂载业务子应用到 /manus） ==========
root_app = FastAPI(
    title="Manus PPT Generator (Root)",
    description="Root app: mount business app under /manus",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
)

# 为根应用添加异常处理器（webhook 路由可能需要）
setup_exception_handlers(root_app)

# 如果 webhook_path 不包含 /manus，在根应用上注册 webhook 路由
# （如果包含 /manus，则已在上面注册到 manus_app）
if not webhook_path.startswith("/manus"):
    root_app.include_router(webhook_router)
    logger.info(f"Webhook 路由注册在 root_app 上，完整路径: {webhook_path}")


@root_app.get("/")
async def root_redirect():
    """根路径重定向到 /manus/（避免用户误访问根路径）"""
    return RedirectResponse(url="/manus/", status_code=307)

# 根应用的 favicon 路由
@root_app.get("/favicon.ico")
async def root_favicon():
    """返回 favicon"""
    favicon_path = STATIC_DIR / "logo" / "logo.png"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/png")
    from fastapi.responses import Response
    return Response(status_code=204)

# Service Worker 路由（避免 404 错误）
@root_app.get("/service-worker.js")
async def service_worker():
    """Service Worker - 返回 204 No Content（当前未实现 PWA）"""
    from fastapi.responses import Response
    return Response(status_code=204)


# 对外统一入口：/manus/*
root_app.mount("/manus", manus_app)

# uvicorn 启动对象
app = root_app

