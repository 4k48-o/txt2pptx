"""
Health Check API - 健康检查接口
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime

from ..config import Settings, get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: datetime
    manus_api_configured: bool


class ConfigResponse(BaseModel):
    """配置信息响应（只返回公开配置）"""
    manus_api_base_url: str
    poll_interval: int
    poll_timeout: int
    output_dir: str
    debug: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    健康检查接口

    返回服务状态和基本信息
    """
    from .. import __version__

    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(),
        manus_api_configured=bool(settings.manus_api_key),
    )


@router.get("/config", response_model=ConfigResponse)
async def get_config(settings: Settings = Depends(get_settings)):
    """
    获取公开配置信息

    不返回敏感信息（如 API Key）
    """
    return ConfigResponse(
        manus_api_base_url=settings.manus_api_base_url,
        poll_interval=settings.poll_interval,
        poll_timeout=settings.poll_timeout,
        output_dir=str(settings.output_dir),
        debug=settings.debug,
    )


@router.get("/test-error")
async def test_error():
    """测试异常处理（仅用于开发）"""
    from ..exceptions import AppException
    raise AppException(
        message="This is a test error",
        code="TEST_ERROR",
        detail="Testing exception handler",
        status_code=400,
    )

