"""
重试工具模块

提供重试装饰器和重试函数，用于处理网络错误、API 错误等可重试的异常
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
from datetime import datetime, timedelta

from ..exceptions import ManusAPIException

logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Tuple[Type[Exception], ...] = (
            ManusAPIException,
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        ),
        retryable_status_codes: Tuple[int, ...] = (500, 502, 503, 504, 429),
    ):
        """
        初始化重试配置

        Args:
            max_retries: 最大重试次数（不包括首次尝试）
            initial_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数退避基数
            retryable_exceptions: 可重试的异常类型
            retryable_status_codes: 可重试的 HTTP 状态码
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions
        self.retryable_status_codes = retryable_status_codes


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    计算重试延迟时间（指数退避）

    Args:
        attempt: 当前尝试次数（从 0 开始）
        config: 重试配置

    Returns:
        延迟时间（秒）
    """
    delay = config.initial_delay * (config.exponential_base ** attempt)
    return min(delay, config.max_delay)


def is_retryable_error(error: Exception, config: RetryConfig) -> bool:
    """
    判断错误是否可重试

    Args:
        error: 异常对象
        config: 重试配置

    Returns:
        是否可重试
    """
    # 检查异常类型
    if isinstance(error, config.retryable_exceptions):
        # 如果是 ManusAPIException，检查状态码
        if isinstance(error, ManusAPIException):
            # 从 detail 中提取状态码（如果可能）
            detail = getattr(error, "detail", "")
            if detail:
                # 尝试从 detail 中提取状态码
                for status_code in config.retryable_status_codes:
                    if str(status_code) in str(detail):
                        return True
            # 默认情况下，ManusAPIException 可重试（5xx 错误）
            return True
        return True
    
    return False


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    operation_name: str = "操作",
    **kwargs,
) -> Any:
    """
    异步函数重试装饰器

    Args:
        func: 要重试的异步函数
        *args: 函数位置参数
        config: 重试配置（如果为 None，使用默认配置）
        operation_name: 操作名称（用于日志）
        **kwargs: 函数关键字参数

    Returns:
        函数返回值

    Raises:
        最后一次尝试的异常
    """
    if config is None:
        config = RetryConfig()

    last_error = None

    for attempt in range(config.max_retries + 1):
        try:
            if attempt > 0:
                delay = calculate_delay(attempt - 1, config)
                logger.info(
                    f"[重试] {operation_name} - 第 {attempt + 1} 次尝试 "
                    f"(延迟 {delay:.2f} 秒)"
                )
                await asyncio.sleep(delay)

            logger.debug(f"[重试] {operation_name} - 尝试 {attempt + 1}/{config.max_retries + 1}")
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"[重试] {operation_name} - 第 {attempt + 1} 次尝试成功")
            
            return result

        except Exception as e:
            last_error = e
            
            if not is_retryable_error(e, config):
                logger.warning(
                    f"[重试] {operation_name} - 遇到不可重试的错误: {type(e).__name__}: {e}"
                )
                raise

            if attempt < config.max_retries:
                logger.warning(
                    f"[重试] {operation_name} - 第 {attempt + 1} 次尝试失败: "
                    f"{type(e).__name__}: {e}，将重试"
                )
            else:
                logger.error(
                    f"[重试] {operation_name} - 所有 {config.max_retries + 1} 次尝试均失败，"
                    f"最后一次错误: {type(e).__name__}: {e}"
                )
                raise

    # 理论上不会到达这里
    if last_error:
        raise last_error
    raise RuntimeError(f"{operation_name} 失败：未知错误")


def retryable(
    config: Optional[RetryConfig] = None,
    operation_name: Optional[str] = None,
):
    """
    重试装饰器（用于异步函数）

    Usage:
        @retryable(operation_name="创建任务")
        async def create_task():
            ...

    Args:
        config: 重试配置
        operation_name: 操作名称（如果为 None，使用函数名）
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            return await retry_async(
                func,
                *args,
                config=config,
                operation_name=op_name,
                **kwargs,
            )
        return wrapper
    return decorator
