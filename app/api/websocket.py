"""
WebSocket API 端点

提供 WebSocket 连接端点，支持：
- 客户端连接
- 心跳检测 (ping/pong)
- 任务订阅/取消订阅
- 接收实时任务更新
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str
):
    """
    WebSocket 连接端点
    
    Args:
        client_id: 客户端唯一标识（由前端生成）
    
    消息格式（客户端发送）:
    ```json
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "task_id": "xxx"  // subscribe/unsubscribe 时需要
    }
    ```
    
    消息格式（服务端推送）:
    ```json
    {
        "type": "connected" | "subscribed" | "task_update" | "task_completed" | "task_failed" | "pong" | "error",
        "task_id": "xxx",
        "data": { ... },
        "timestamp": "2026-01-14T12:00:00"
    }
    ```
    """
    # 建立连接
    connected = await manager.connect(client_id, websocket)
    if not connected:
        return
    
    try:
        # 启动心跳检测任务
        heartbeat_task = asyncio.create_task(
            _heartbeat_checker(client_id, websocket)
        )
        
        # 监听客户端消息
        while True:
            try:
                # 接收消息（带超时，用于检测连接状态）
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60秒超时
                )
                
                # 解析并处理消息
                await _handle_client_message(client_id, data)
                
            except asyncio.TimeoutError:
                # 超时，发送心跳检测
                try:
                    await manager.send_to_client(client_id, {
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket 客户端断开: client_id={client_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: client_id={client_id}, error={e}")
    finally:
        # 取消心跳任务
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        # 清理连接
        await manager.disconnect(client_id)


async def _handle_client_message(client_id: str, raw_data: str):
    """
    处理客户端发送的消息
    
    Args:
        client_id: 客户端 ID
        raw_data: 原始消息字符串
    """
    try:
        message = json.loads(raw_data)
    except json.JSONDecodeError:
        await manager.send_to_client(client_id, {
            "type": "error",
            "message": "无效的 JSON 格式",
            "timestamp": datetime.now().isoformat()
        })
        return
    
    action = message.get("action")
    task_id = message.get("task_id")
    
    if action == "subscribe":
        if not task_id:
            await manager.send_to_client(client_id, {
                "type": "error",
                "message": "订阅需要提供 task_id",
                "timestamp": datetime.now().isoformat()
            })
            return
        await manager.subscribe_task(client_id, task_id)
        
    elif action == "unsubscribe":
        if not task_id:
            await manager.send_to_client(client_id, {
                "type": "error",
                "message": "取消订阅需要提供 task_id",
                "timestamp": datetime.now().isoformat()
            })
            return
        await manager.unsubscribe_task(client_id, task_id)
        
    elif action == "ping":
        await manager.send_to_client(client_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
        
    elif action == "pong":
        # 前端对 ping 的响应，静默接受即可
        logger.debug(f"收到心跳响应: client_id={client_id}")
        
    elif action == "stats":
        # 获取连接统计（调试用）
        stats = manager.get_stats()
        await manager.send_to_client(client_id, {
            "type": "stats",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        })
        
    else:
        await manager.send_to_client(client_id, {
            "type": "error",
            "message": f"未知的 action: {action}",
            "timestamp": datetime.now().isoformat()
        })


async def _heartbeat_checker(client_id: str, websocket: WebSocket):
    """
    心跳检测任务
    
    定期检查连接是否存活
    """
    while True:
        try:
            await asyncio.sleep(30)  # 每30秒检测一次
            
            if not manager.is_connected(client_id):
                break
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"心跳检测错误: client_id={client_id}, error={e}")
            break


# === 辅助 API 端点 ===

@router.get("/ws/stats", tags=["WebSocket"])
async def get_websocket_stats():
    """获取 WebSocket 连接统计信息"""
    return {
        "success": True,
        "data": manager.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

