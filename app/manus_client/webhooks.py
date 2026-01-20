"""
Manus Webhook API 客户端

用于向 Manus API 注册和管理 Webhook
"""

import logging
from typing import Optional, List, Dict, Any

from .client import AsyncManusClient

logger = logging.getLogger(__name__)


class AsyncWebhookManager:
    """异步 Webhook 管理器"""
    
    def __init__(self, client: AsyncManusClient):
        self.client = client
    
    async def create_webhook(self, url: str) -> Dict[str, Any]:
        """
        创建 Webhook
        
        Args:
            url: Webhook 回调 URL（必须是公网可访问的 HTTPS 地址）
            
        Returns:
            创建结果，包含 webhook_id
        """
        logger.info(f"创建 Webhook: url={url}")
        
        response = await self.client.post(
            "/v1/webhooks",
            data={
                "webhook": {
                    "url": url
                }
            }
        )
        
        webhook_id = response.get("webhook_id") or response.get("id")
        logger.info(f"Webhook 创建成功: webhook_id={webhook_id}")
        
        return response
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """
        删除 Webhook
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            是否删除成功
        """
        logger.info(f"删除 Webhook: webhook_id={webhook_id}")
        
        try:
            await self.client.delete(f"/v1/webhooks/{webhook_id}")
            logger.info(f"Webhook 删除成功: webhook_id={webhook_id}")
            return True
        except Exception as e:
            logger.error(f"删除 Webhook 失败: {e}")
            return False
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        获取 Webhook 列表
        
        注意：Manus API 不支持查询 Webhook 列表（GET /v1/webhooks 返回 405），
        此方法已废弃，保留仅为兼容性，实际无法使用。
        
        Returns:
            Webhook 列表（始终返回空列表）
        """
        logger.warning("list_webhooks() 已废弃：Manus API 不支持查询 Webhook 列表")
        return []


# ========== Webhook 自动注册 ==========

_registered_webhook_id: Optional[str] = None


async def register_webhook_on_startup(client: AsyncManusClient) -> Optional[str]:
    """
    应用启动时自动注册 Webhook
    
    注意：如果 Webhook 已存在（409 错误），会视为注册成功。
    由于 Manus API 不支持查询 Webhook 列表，无法获取已存在 Webhook 的 webhook_id。
    Webhook 是持久化的，不需要在应用关闭时删除。
    
    Returns:
        新创建成功返回 webhook_id，已存在返回空字符串 ""，失败返回 None
    """
    global _registered_webhook_id
    
    from app.config import get_settings
    from app.exceptions import ManusAPIException
    
    settings = get_settings()
    
    if not settings.webhook_enabled:
        logger.info("Webhook 未启用，跳过注册")
        return None
    
    if not settings.webhook_base_url:
        logger.warning("WEBHOOK_BASE_URL 未配置，无法注册 Webhook")
        return None
    
    # 构建完整的对外 Webhook URL（包含 app_base_path，例如 /manus）
    webhook_url = settings.webhook_callback_url()
    
    logger.info(f"准备注册 Webhook: {webhook_url}")
    
    webhook_manager = AsyncWebhookManager(client)
    
    try:
        # 尝试创建 Webhook
        result = await webhook_manager.create_webhook(webhook_url)
        
        _registered_webhook_id = result.get("webhook_id") or result.get("id")
        logger.info(f"Webhook 注册成功: webhook_id={_registered_webhook_id}")
        
        return _registered_webhook_id
        
    except ManusAPIException as e:
        # 如果是因为 Webhook 已存在（409），视为注册成功
        if "409" in str(e.message) or (e.detail and "already exists" in str(e.detail).lower()):
            logger.info(
                f"Webhook 已存在（409），视为注册成功: {webhook_url}。"
                f"注意：Manus API 不支持查询 Webhook 列表，无法获取 webhook_id。"
            )
            # 不设置 _registered_webhook_id，因为无法获取
            # 返回空字符串表示成功但无 webhook_id
            return ""
        else:
            # 其他错误，记录并返回 None
            logger.error(f"Webhook 注册失败: {e.message}, detail={e.detail}")
            return None
            
    except Exception as e:
        logger.error(f"Webhook 注册失败: {e}")
        return None


async def unregister_webhook_on_shutdown(client: AsyncManusClient) -> bool:
    """
    应用关闭时注销 Webhook
    """
    global _registered_webhook_id
    
    if not _registered_webhook_id:
        return True
    
    try:
        webhook_manager = AsyncWebhookManager(client)
        result = await webhook_manager.delete_webhook(_registered_webhook_id)
        
        if result:
            logger.info(f"Webhook 注销成功: webhook_id={_registered_webhook_id}")
            _registered_webhook_id = None
            
        return result
        
    except Exception as e:
        logger.error(f"Webhook 注销失败: {e}")
        return False


def get_registered_webhook_id() -> Optional[str]:
    """获取已注册的 Webhook ID"""
    return _registered_webhook_id

