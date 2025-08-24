"""
后台任务管理器
解决后台任务未受控创建和异常处理问题
"""

import asyncio
import weakref
from typing import Dict, Set, Optional, Callable, Any
from loguru import logger
from datetime import datetime


class TaskManager:
    """后台任务管理器，提供任务生命周期管理"""
    
    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_metadata: Dict[str, Dict[str, Any]] = {}
        self._cleanup_callbacks: Dict[str, Callable] = {}
        
    async def create_task(
        self, 
        task_id: str, 
        coro, 
        task_type: str = "background",
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_callback: Optional[Callable] = None
    ) -> asyncio.Task:
        """
        创建并跟踪后台任务
        
        Args:
            task_id: 任务唯一标识
            coro: 协程对象
            task_type: 任务类型
            metadata: 任务元数据
            cleanup_callback: 任务完成后的清理回调
        """
        if task_id in self._running_tasks:
            existing_task = self._running_tasks[task_id]
            if not existing_task.done():
                logger.warning(f"任务 {task_id} 已存在且正在运行，取消旧任务")
                existing_task.cancel()
        
        # 创建任务
        task = asyncio.create_task(coro, name=task_id)
        
        # 保存任务引用和元数据
        self._running_tasks[task_id] = task
        self._task_metadata[task_id] = {
            "type": task_type,
            "created_at": datetime.now(),
            "metadata": metadata or {}
        }
        
        if cleanup_callback:
            self._cleanup_callbacks[task_id] = cleanup_callback
        
        # 添加完成回调
        task.add_done_callback(lambda t: self._task_done_callback(task_id, t))
        
        logger.info(f"创建后台任务: {task_id} ({task_type})")
        return task
    
    def _task_done_callback(self, task_id: str, task: asyncio.Task):
        """任务完成回调"""
        try:
            # 检查任务异常
            if task.cancelled():
                logger.info(f"任务 {task_id} 已取消")
            elif task.exception():
                exc = task.exception()
                logger.error(f"任务 {task_id} 执行异常: {exc}")
            else:
                logger.info(f"任务 {task_id} 执行完成")
                
        except Exception as e:
            logger.error(f"任务回调处理异常: {e}")
        finally:
            # 清理任务记录
            self._cleanup_task(task_id)
    
    def _cleanup_task(self, task_id: str):
        """清理任务记录"""
        try:
            # 执行清理回调
            if task_id in self._cleanup_callbacks:
                callback = self._cleanup_callbacks.pop(task_id)
                if callback:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"任务 {task_id} 清理回调异常: {e}")
            
            # 移除任务记录
            self._running_tasks.pop(task_id, None)
            self._task_metadata.pop(task_id, None)
            
        except Exception as e:
            logger.error(f"清理任务 {task_id} 时异常: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self._running_tasks:
            return None
            
        task = self._running_tasks[task_id]
        metadata = self._task_metadata.get(task_id, {})
        
        status = "running"
        if task.done():
            if task.cancelled():
                status = "cancelled"
            elif task.exception():
                status = "failed"
            else:
                status = "completed"
        
        return {
            "task_id": task_id,
            "status": status,
            "type": metadata.get("type", "unknown"),
            "created_at": metadata.get("created_at"),
            "metadata": metadata.get("metadata", {})
        }
    
    def list_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """列出所有正在运行的任务"""
        result = {}
        for task_id in list(self._running_tasks.keys()):
            status = self.get_task_status(task_id)
            if status and status["status"] == "running":
                result[task_id] = status
        return result
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self._running_tasks:
            return False
            
        task = self._running_tasks[task_id]
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"已取消任务: {task_id}")
            return True
        return False
    
    async def shutdown(self):
        """关闭任务管理器，取消所有运行中的任务"""
        logger.info("正在关闭任务管理器...")
        
        # 取消所有运行中的任务
        running_tasks = list(self._running_tasks.values())
        for task in running_tasks:
            if not task.done():
                task.cancel()
        
        # 等待所有任务完成
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)
        
        # 清理所有记录
        self._running_tasks.clear()
        self._task_metadata.clear()
        self._cleanup_callbacks.clear()
        
        logger.info("任务管理器已关闭")


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


async def cleanup_task_manager():
    """清理任务管理器"""
    global _task_manager
    if _task_manager:
        await _task_manager.shutdown()
        _task_manager = None