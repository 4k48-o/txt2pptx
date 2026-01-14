"""
WebSocket 连接管理器

管理 WebSocket 连接池，支持：
- 客户端连接/断开管理
- 按任务 ID 订阅/取消订阅
- 广播消息
- 定向推送（按客户端或任务）
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 活跃连接: client_id -> WebSocket
        self._active_connections: Dict[str, WebSocket] = {}
        
        # 任务订阅: task_id -> Set[client_id]
        self._task_subscriptions: Dict[str, Set[str]] = {}
        
        # 客户端订阅的任务: client_id -> Set[task_id]
        self._client_tasks: Dict[str, Set[str]] = {}
        
        # 连接锁，防止并发问题
        self._lock = asyncio.Lock()
    
    @property
    def active_count(self) -> int:
        """当前活跃连接数"""
        return len(self._active_connections)
    
    async def connect(self, client_id: str, websocket: WebSocket) -> bool:
        """
        接受新的 WebSocket 连接
        
        Args:
            client_id: 客户端唯一标识
            websocket: WebSocket 连接对象
            
        Returns:
            是否连接成功
        """
        try:
            await websocket.accept()
            
            async with self._lock:
                # 如果已存在相同 client_id，先断开旧连接
                if client_id in self._active_connections:
                    old_ws = self._active_connections[client_id]
                    try:
                        await old_ws.close(code=1000, reason="新连接替换")
                    except Exception:
                        pass
                
                self._active_connections[client_id] = websocket
                self._client_tasks[client_id] = set()
            
            logger.info(f"WebSocket 连接成功: client_id={client_id}, 当前连接数={self.active_count}")
            
            # 发送连接确认消息
            await self.send_to_client(client_id, {
                "type": "connected",
                "client_id": client_id,
                "message": "WebSocket 连接成功",
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket 连接失败: client_id={client_id}, error={e}")
            return False
    
    async def disconnect(self, client_id: str):
        """
        断开 WebSocket 连接
        
        Args:
            client_id: 客户端唯一标识
        """
        async with self._lock:
            if client_id not in self._active_connections:
                return
            
            # 移除连接
            del self._active_connections[client_id]
            
            # 清理该客户端的所有任务订阅
            if client_id in self._client_tasks:
                for task_id in self._client_tasks[client_id]:
                    if task_id in self._task_subscriptions:
                        self._task_subscriptions[task_id].discard(client_id)
                        # 如果任务没有订阅者了，清理
                        if not self._task_subscriptions[task_id]:
                            del self._task_subscriptions[task_id]
                del self._client_tasks[client_id]
        
        logger.info(f"WebSocket 断开连接: client_id={client_id}, 当前连接数={self.active_count}")
    
    async def subscribe_task(self, client_id: str, task_id: str):
        """
        订阅任务更新
        
        Args:
            client_id: 客户端唯一标识
            task_id: 任务 ID
        """
        async with self._lock:
            if client_id not in self._active_connections:
                logger.warning(f"订阅失败: client_id={client_id} 未连接")
                return
            
            # 添加任务订阅
            if task_id not in self._task_subscriptions:
                self._task_subscriptions[task_id] = set()
            self._task_subscriptions[task_id].add(client_id)
            
            # 记录客户端订阅的任务
            self._client_tasks[client_id].add(task_id)
        
        logger.debug(f"任务订阅: client_id={client_id}, task_id={task_id}")
        
        # 发送订阅确认
        await self.send_to_client(client_id, {
            "type": "subscribed",
            "task_id": task_id,
            "message": f"已订阅任务 {task_id} 的更新",
            "timestamp": datetime.now().isoformat()
        })
    
    async def unsubscribe_task(self, client_id: str, task_id: str):
        """
        取消订阅任务更新
        
        Args:
            client_id: 客户端唯一标识
            task_id: 任务 ID
        """
        async with self._lock:
            if task_id in self._task_subscriptions:
                self._task_subscriptions[task_id].discard(client_id)
                if not self._task_subscriptions[task_id]:
                    del self._task_subscriptions[task_id]
            
            if client_id in self._client_tasks:
                self._client_tasks[client_id].discard(task_id)
        
        logger.debug(f"取消订阅: client_id={client_id}, task_id={task_id}")
    
    async def send_to_client(self, client_id: str, message: dict) -> bool:
        """
        向指定客户端发送消息
        
        Args:
            client_id: 客户端唯一标识
            message: 消息内容（字典）
            
        Returns:
            是否发送成功
        """
        if client_id not in self._active_connections:
            logger.warning(f"发送失败: client_id={client_id} 未连接")
            return False
        
        websocket = self._active_connections[client_id]
        try:
            await websocket.send_json(message)
            logger.debug(f"消息已发送: client_id={client_id}, type={message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: client_id={client_id}, error={e}")
            # 发送失败，可能连接已断开，清理
            await self.disconnect(client_id)
            return False
    
    async def send_to_task_subscribers(self, task_id: str, message: dict) -> int:
        """
        向所有订阅指定任务的客户端发送消息
        
        Args:
            task_id: 任务 ID
            message: 消息内容（字典）
            
        Returns:
            成功发送的客户端数量
        """
        if task_id not in self._task_subscriptions:
            logger.debug(f"任务无订阅者: task_id={task_id}")
            return 0
        
        # 复制订阅者列表，避免迭代时修改
        subscribers = list(self._task_subscriptions.get(task_id, set()))
        
        success_count = 0
        for client_id in subscribers:
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        logger.info(f"任务消息推送: task_id={task_id}, 订阅者={len(subscribers)}, 成功={success_count}")
        return success_count
    
    async def broadcast(self, message: dict) -> int:
        """
        向所有连接的客户端广播消息
        
        Args:
            message: 消息内容（字典）
            
        Returns:
            成功发送的客户端数量
        """
        # 复制连接列表，避免迭代时修改
        clients = list(self._active_connections.keys())
        
        success_count = 0
        for client_id in clients:
            if await self.send_to_client(client_id, message):
                success_count += 1
        
        logger.info(f"广播消息: 客户端总数={len(clients)}, 成功={success_count}")
        return success_count
    
    def is_connected(self, client_id: str) -> bool:
        """检查客户端是否已连接"""
        return client_id in self._active_connections
    
    def get_task_subscribers(self, task_id: str) -> Set[str]:
        """获取任务的所有订阅者"""
        return self._task_subscriptions.get(task_id, set()).copy()
    
    def get_client_tasks(self, client_id: str) -> Set[str]:
        """获取客户端订阅的所有任务"""
        return self._client_tasks.get(client_id, set()).copy()
    
    def get_stats(self) -> dict:
        """获取连接统计信息"""
        return {
            "active_connections": self.active_count,
            "task_subscriptions": len(self._task_subscriptions),
            "clients": list(self._active_connections.keys()),
            "tasks_with_subscribers": list(self._task_subscriptions.keys())
        }


# 全局单例实例
manager = ConnectionManager()

