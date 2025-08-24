"""
WebSocket API路由
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from loguru import logger

router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
    
    async def broadcast(self, message: str):
        """广播消息"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/tasks")
async def websocket_tasks(websocket: WebSocket):
    """
    任务进度WebSocket端点
    
    客户端可以通过此端点接收任务状态更新
    """
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            
            # 如果收到ping消息，返回pong
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # 处理其他消息类型
                logger.debug(f"收到WebSocket消息: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)


async def send_task_update(task_id: str, status: str, progress: int = 0, message: str = ""):
    """
    发送任务更新消息
    
    这个函数可以被其他模块调用来发送任务状态更新
    """
    event = {
        "type": "task_progress",
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message,
        "timestamp": "2023-01-01T00:00:00Z"  # TODO: 使用真实时间戳
    }
    
    message_str = json.dumps(event)
    await manager.broadcast(message_str)


async def send_task_completed(task_id: str, message: str = "任务已完成"):
    """发送任务完成消息"""
    await send_task_update(task_id, "completed", 100, message)


async def send_task_failed(task_id: str, error_message: str):
    """发送任务失败消息"""
    await send_task_update(task_id, "failed", 0, f"任务失败: {error_message}")