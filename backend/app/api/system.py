"""
系统管理API路由
"""

import os
import psutil
import socket
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings
from app.core.database import backup_database, get_database_stats, restore_database_from_backup

router = APIRouter()


class ProcessInfo(BaseModel):
    """进程信息模型"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: str
    cmdline: List[str]


class PortInfo(BaseModel):
    """端口信息模型"""
    port: int
    protocol: str
    status: str
    pid: Optional[int] = None
    process_name: Optional[str] = None


class SystemStats(BaseModel):
    """系统统计信息"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    boot_time: str
    uptime: float


class BackupRequest(BaseModel):
    """备份请求模型"""
    description: Optional[str] = None


class RestoreRequest(BaseModel):
    """恢复请求模型"""
    backup_path: str


@router.get("/stats", response_model=SystemStats, summary="系统统计信息")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # 网络统计
        network = psutil.net_io_counters()
        
        # 系统启动时间
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = (datetime.now() - boot_time).total_seconds()
        
        return SystemStats(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            network_sent=network.bytes_sent,
            network_recv=network.bytes_recv,
            boot_time=boot_time.isoformat(),
            uptime=uptime
        )
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")


@router.get("/processes", response_model=List[ProcessInfo], summary="进程列表")
async def get_processes():
    """获取系统进程列表"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'create_time', 'cmdline']):
            try:
                info = proc.info
                if info['name'] and 'python' in info['name'].lower():  # 只显示Python相关进程
                    processes.append(ProcessInfo(
                        pid=info['pid'],
                        name=info['name'] or 'Unknown',
                        status=info['status'] or 'Unknown',
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_percent=info['memory_percent'] or 0.0,
                        create_time=datetime.fromtimestamp(info['create_time']).isoformat() if info['create_time'] else '',
                        cmdline=info['cmdline'] or []
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    except Exception as e:
        logger.error(f"获取进程列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取进程列表失败: {str(e)}")


@router.get("/ports", response_model=List[PortInfo], summary="端口使用情况")
async def get_ports():
    """获取端口使用情况"""
    try:
        ports = []
        connections = psutil.net_connections(kind='inet')
        
        for conn in connections:
            if conn.laddr and conn.laddr.port:
                try:
                    process_name = None
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            process_name = proc.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    ports.append(PortInfo(
                        port=conn.laddr.port,
                        protocol=conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                        status=conn.status,
                        pid=conn.pid,
                        process_name=process_name
                    ))
                except Exception:
                    continue
        
        # 去重并排序
        unique_ports = {}
        for port in ports:
            key = (port.port, port.protocol)
            if key not in unique_ports:
                unique_ports[key] = port
        
        return sorted(unique_ports.values(), key=lambda x: x.port)
    except Exception as e:
        logger.error(f"获取端口信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取端口信息失败: {str(e)}")


@router.post("/ports/{port}/check", summary="检查端口是否可用")
async def check_port_available(port: int):
    """检查指定端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            available = result != 0
            
        return {
            "port": port,
            "available": available,
            "message": "端口可用" if available else "端口被占用"
        }
    except Exception as e:
        logger.error(f"检查端口失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查端口失败: {str(e)}")


@router.post("/process/{pid}/kill", summary="终止进程")
async def kill_process(pid: int):
    """终止指定进程"""
    try:
        process = psutil.Process(pid)
        process_name = process.name()
        
        # 安全检查：只允许终止Python进程
        if 'python' not in process_name.lower():
            raise HTTPException(status_code=403, detail="仅允许终止Python进程")
        
        process.terminate()
        
        # 等待进程终止
        try:
            process.wait(timeout=5)
        except psutil.TimeoutExpired:
            # 强制终止
            process.kill()
        
        return {
            "pid": pid,
            "name": process_name,
            "message": "进程已终止"
        }
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail="进程不存在")
    except psutil.AccessDenied:
        raise HTTPException(status_code=403, detail="无权限终止进程")
    except Exception as e:
        logger.error(f"终止进程失败: {e}")
        raise HTTPException(status_code=500, detail=f"终止进程失败: {str(e)}")


@router.post("/database/backup", summary="备份数据库")
async def create_backup(request: BackupRequest):
    """创建数据库备份"""
    try:
        backup_path = await backup_database()
        
        return {
            "backup_path": backup_path,
            "message": "数据库备份成功",
            "timestamp": datetime.now().isoformat(),
            "description": request.description
        }
    except Exception as e:
        logger.error(f"数据库备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库备份失败: {str(e)}")


@router.post("/database/restore", summary="恢复数据库")
async def restore_backup(request: RestoreRequest):
    """从备份恢复数据库"""
    try:
        success = await restore_database_from_backup(request.backup_path)
        
        if success:
            return {
                "backup_path": request.backup_path,
                "message": "数据库恢复成功",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="数据库恢复失败")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="备份文件不存在")
    except Exception as e:
        logger.error(f"数据库恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库恢复失败: {str(e)}")


@router.get("/database/backups", summary="获取备份列表")
async def list_backups():
    """获取可用的数据库备份列表"""
    try:
        from pathlib import Path
        
        backup_dir = settings.BACKUP_DIR
        if not backup_dir.exists():
            return {"backups": []}
        
        backups = []
        for backup_file in backup_dir.glob("*.duckdb"):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # 按创建时间排序
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return {"backups": backups}
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")


@router.get("/database/stats", summary="数据库统计信息")
async def get_db_stats():
    """获取数据库统计信息"""
    try:
        stats = await get_database_stats()
        return {"stats": stats}
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据库统计失败: {str(e)}")


@router.post("/shutdown", summary="关闭服务")
async def shutdown_service():
    """关闭服务（仅在调试模式下可用）"""
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="生产模式下不允许远程关闭服务")
    
    try:
        logger.info("收到关闭服务请求")
        
        # 返回响应后关闭
        import asyncio
        asyncio.create_task(_delayed_shutdown())
        
        return {"message": "服务将在1秒后关闭"}
    except Exception as e:
        logger.error(f"关闭服务失败: {e}")
        raise HTTPException(status_code=500, detail=f"关闭服务失败: {str(e)}")


async def _delayed_shutdown():
    """延迟关闭服务"""
    import asyncio
    await asyncio.sleep(1)
    logger.info("正在关闭服务...")
    os._exit(0)