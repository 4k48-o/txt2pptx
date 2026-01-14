"""
Manus API Client - 基础客户端类
"""

import requests
from typing import Optional, Dict, Any
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ManusClient:
    """Manus API 基础客户端"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化 Manus API 客户端

        Args:
            api_key: Manus API Key，如果不传则从环境变量读取
            base_url: API Base URL，如果不传则从环境变量读取
        """
        self.config = Config()
        self.api_key = api_key or self.config.manus_api_key
        self.base_url = base_url or self.config.manus_api_base_url

        if not self.api_key:
            raise ValueError("MANUS_API_KEY is required")

        self.session = requests.Session()
        self.session.headers.update({
            "API_KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

        logger.info("Manus API Client initialized")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发送 API 请求

        Args:
            method: HTTP 方法 (GET, POST, DELETE 等)
            endpoint: API 端点 (如 /v1/tasks)
            data: 请求体数据
            params: 查询参数

        Returns:
            API 响应的 JSON 数据

        Raises:
            requests.HTTPError: 请求失败时抛出
        """
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"Request: {method} {url}")

        response = self.session.request(
            method=method,
            url=url,
            json=data,
            params=params,
        )

        response.raise_for_status()

        logger.debug(f"Response: {response.status_code}")

        return response.json()

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET 请求"""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST 请求"""
        return self._request("POST", endpoint, data=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE 请求"""
        return self._request("DELETE", endpoint)

