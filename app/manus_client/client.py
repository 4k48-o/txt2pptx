"""
Async Manus API Client - 异步基础客户端
"""

import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import httpx

from ..config import Settings, get_settings
from ..exceptions import ManusAPIException, ConfigurationException

logger = logging.getLogger(__name__)


class AsyncManusClient:
    """异步 Manus API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        settings: Optional[Settings] = None,
    ):
        """
        初始化异步 Manus API 客户端

        Args:
            api_key: Manus API Key，如果不传则从配置读取
            base_url: API Base URL，如果不传则从配置读取
            settings: 配置对象
        """
        self._settings = settings or get_settings()
        self.api_key = api_key or self._settings.manus_api_key
        self.base_url = base_url or self._settings.manus_api_base_url

        if not self.api_key:
            raise ConfigurationException("MANUS_API_KEY is required")

        self._client: Optional[httpx.AsyncClient] = None

        logger.info("AsyncManusClient initialized")

    @property
    def headers(self) -> Dict[str, str]:
        """请求头"""
        return {
            "API_KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=httpx.Timeout(60.0),  # 60 秒超时
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.debug("AsyncManusClient connection closed")

    @asynccontextmanager
    async def session(self):
        """上下文管理器，自动管理连接"""
        try:
            yield self
        finally:
            await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发送异步 API 请求

        Args:
            method: HTTP 方法 (GET, POST, DELETE 等)
            endpoint: API 端点 (如 /v1/tasks)
            data: 请求体数据
            params: 查询参数

        Returns:
            API 响应的 JSON 数据

        Raises:
            ManusAPIException: API 请求失败时抛出
        """
        client = await self._get_client()
        url = endpoint

        logger.debug(f"Request: {method} {self.base_url}{url}")

        try:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
            )

            logger.debug(f"Response: {response.status_code}")

            # 检查响应状态
            if response.status_code >= 400:
                error_detail = None
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail") or error_data.get("message")
                except Exception:
                    error_detail = response.text[:200]

                # 记录 Manus API 错误的详细信息，便于排查（例如 429 限流）
                logger.error(
                    "Manus API error %s for %s %s - detail: %s",
                    response.status_code,
                    method,
                    url,
                    error_detail,
                )

                raise ManusAPIException(
                    message=f"Manus API error: {response.status_code}",
                    detail=error_detail,
                )

            return response.json()

        except httpx.TimeoutException as e:
            raise ManusAPIException(
                message="Manus API request timeout",
                detail=str(e),
            )
        except httpx.HTTPError as e:
            raise ManusAPIException(
                message="Manus API request failed",
                detail=str(e),
            )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """GET 请求"""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST 请求"""
        return await self._request("POST", endpoint, data=data)

    async def delete(
        self,
        endpoint: str,
    ) -> Dict[str, Any]:
        """DELETE 请求"""
        return await self._request("DELETE", endpoint)

    async def put_file(
        self,
        url: str,
        file_content: bytes,
    ) -> None:
        """
        上传文件到指定 URL (用于 S3 presigned URL)

        Args:
            url: 上传 URL
            file_content: 文件内容
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await client.put(url, content=file_content)
            response.raise_for_status()

