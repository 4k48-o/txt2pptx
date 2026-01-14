"""
Exception Handlers - 全局异常处理
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: str


class AppException(Exception):
    """应用自定义异常基类"""
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        detail: Optional[str] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class ManusAPIException(AppException):
    """Manus API 调用异常"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            code="MANUS_API_ERROR",
            detail=detail,
            status_code=502,
        )


class TaskNotFoundException(AppException):
    """任务不存在异常"""
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            code="TASK_NOT_FOUND",
            status_code=404,
        )


class FileUploadException(AppException):
    """文件上传异常"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            code="FILE_UPLOAD_ERROR",
            detail=detail,
            status_code=400,
        )


class ConfigurationException(AppException):
    """配置异常"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理应用自定义异常"""
        logger.error(f"AppException: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.message,
                detail=exc.detail,
                code=exc.code,
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 HTTP 异常"""
        logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=str(exc.detail),
                code=f"HTTP_{exc.status_code}",
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                detail=str(exc) if app.debug else None,
                code="INTERNAL_ERROR",
            ).model_dump(),
        )

