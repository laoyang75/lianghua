"""
改进的进程和端口管理器
解决现有进程管理中的问题
"""

import asyncio
import socket
import psutil
import subprocess
import time
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from loguru import logger
import json


class ProcessManager:
    """改进的进程管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pid_file = project_root / ".process_manager.json"
        
    def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result != 0  # 0表示连接成功，即端口被占用
        except Exception:
            return False
    
    def find_available_port(self, start_port: int, max_attempts: int = 100) -> Optional[int]:
        """寻找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port):
                return port
        return None
    
    def get_process_by_port(self, port: int) -> Optional[psutil.Process]:
        """根据端口查找进程"""
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info['connections'] or []:
                    if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def is_backend_process(self, proc: psutil.Process) -> bool:
        """判断是否为后端服务进程"""
        try:
            cmdline = proc.cmdline()
            # 检查命令行是否包含后端服务的特征
            return any("main.py" in arg and "backend" in arg for arg in cmdline)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def get_service_info(self, service_name: str) -> Optional[Dict]:
        """获取服务信息"""
        try:
            if not self.pid_file.exists():
                return None
                
            with open(self.pid_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(service_name)
        except Exception as e:
            logger.error(f"读取服务信息失败: {e}")
            return None
    
    def save_service_info(self, service_name: str, info: Dict):
        """保存服务信息"""
        try:
            data = {}
            if self.pid_file.exists():
                with open(self.pid_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data[service_name] = info
            
            with open(self.pid_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存服务信息失败: {e}")
    
    def remove_service_info(self, service_name: str):
        """移除服务信息"""
        try:
            if not self.pid_file.exists():
                return
                
            with open(self.pid_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if service_name in data:
                del data[service_name]
                
                if data:
                    with open(self.pid_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    self.pid_file.unlink()
                    
        except Exception as e:
            logger.error(f"移除服务信息失败: {e}")
    
    def get_running_backend_services(self) -> List[Tuple[int, int]]:  # (pid, port)
        """获取所有正在运行的后端服务"""
        services = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
            try:
                if self.is_backend_process(psutil.Process(proc.info['pid'])):
                    # 查找监听端口
                    for conn in proc.info.get('connections', []):
                        if conn.status == psutil.CONN_LISTEN:
                            services.append((proc.info['pid'], conn.laddr.port))
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return services
    
    async def start_backend_service(
        self, 
        port: Optional[int] = None, 
        host: str = "127.0.0.1",
        debug: bool = False
    ) -> Tuple[bool, Dict]:
        """
        启动后端服务
        返回: (成功标志, 服务信息)
        """
        # 检查现有服务
        existing_services = self.get_running_backend_services()
        if existing_services:
            pid, existing_port = existing_services[0]
            logger.warning(f"后端服务已在运行 (PID: {pid}, 端口: {existing_port})")
            return True, {
                "pid": pid,
                "port": existing_port,
                "host": host,
                "status": "running",
                "start_time": time.time()
            }
        
        # 确定端口
        if port is None:
            port = 5318  # 默认端口
        
        if not self.is_port_available(port, host):
            logger.error(f"端口 {port} 被占用")
            # 尝试查找可用端口
            available_port = self.find_available_port(5318)
            if available_port:
                logger.info(f"使用替代端口: {available_port}")
                port = available_port
            else:
                return False, {"error": "无可用端口"}
        
        # 构建启动命令
        backend_main = self.project_root / "backend" / "app" / "main.py"
        if not backend_main.exists():
            return False, {"error": "后端主程序不存在"}
        
        cmd = [
            "python", str(backend_main),
            "--port", str(port),
            "--host", host
        ]
        
        if debug:
            cmd.append("--debug")
        
        try:
            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # 等待服务启动
            start_time = time.time()
            timeout = 30  # 30秒超时
            
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    # 进程已退出
                    stdout, stderr = process.communicate()
                    logger.error(f"后端服务启动失败: {stderr.decode('utf-8', errors='ignore')}")
                    return False, {"error": "进程启动失败"}
                
                # 检查服务是否可访问
                if await self._check_service_health(host, port):
                    break
                    
                await asyncio.sleep(1)
            else:
                # 超时
                process.terminate()
                return False, {"error": "服务启动超时"}
            
            # 保存服务信息
            service_info = {
                "pid": process.pid,
                "port": port,
                "host": host,
                "status": "running",
                "start_time": time.time(),
                "cmd": cmd
            }
            
            self.save_service_info("backend", service_info)
            
            logger.info(f"后端服务启动成功 (PID: {process.pid}, 端口: {port})")
            return True, service_info
            
        except Exception as e:
            logger.error(f"启动后端服务失败: {e}")
            return False, {"error": str(e)}
    
    async def _check_service_health(self, host: str, port: int) -> bool:
        """检查服务健康状态"""
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"http://{host}:{port}/healthz") as resp:
                    return resp.status == 200
        except:
            return False
    
    async def stop_backend_service(self, force: bool = False) -> bool:
        """停止后端服务"""
        service_info = self.get_service_info("backend")
        if not service_info:
            # 尝试查找运行中的服务
            services = self.get_running_backend_services()
            if not services:
                logger.info("没有找到运行中的后端服务")
                return True
            pid, port = services[0]
        else:
            pid = service_info["pid"]
        
        try:
            proc = psutil.Process(pid)
            if proc.is_running():
                if force:
                    proc.kill()
                    logger.info(f"强制终止后端服务 (PID: {pid})")
                else:
                    proc.terminate()
                    # 等待进程优雅退出
                    try:
                        proc.wait(timeout=10)
                        logger.info(f"后端服务已停止 (PID: {pid})")
                    except psutil.TimeoutExpired:
                        proc.kill()
                        logger.info(f"后端服务超时，强制终止 (PID: {pid})")
            
            # 清理服务信息
            self.remove_service_info("backend")
            return True
            
        except psutil.NoSuchProcess:
            logger.info(f"进程 {pid} 已不存在")
            self.remove_service_info("backend")
            return True
        except Exception as e:
            logger.error(f"停止后端服务失败: {e}")
            return False
    
    def get_backend_status(self) -> Dict:
        """获取后端服务状态"""
        service_info = self.get_service_info("backend")
        if not service_info:
            # 检查是否有运行中的服务未记录
            services = self.get_running_backend_services()
            if services:
                pid, port = services[0]
                return {
                    "status": "running",
                    "pid": pid,
                    "port": port,
                    "managed": False  # 表示不是由管理器启动的
                }
            return {"status": "stopped"}
        
        pid = service_info["pid"]
        try:
            proc = psutil.Process(pid)
            if proc.is_running() and self.is_backend_process(proc):
                return {
                    "status": "running",
                    "pid": pid,
                    "port": service_info["port"],
                    "host": service_info["host"],
                    "start_time": service_info["start_time"],
                    "managed": True
                }
            else:
                # 进程不存在或不是后端服务，清理记录
                self.remove_service_info("backend")
                return {"status": "stopped"}
        except psutil.NoSuchProcess:
            self.remove_service_info("backend")
            return {"status": "stopped"}


# 使用示例和测试
async def test_process_manager():
    """测试进程管理器"""
    pm = ProcessManager(Path.cwd())
    
    # 检查状态
    status = pm.get_backend_status()
    print(f"当前状态: {status}")
    
    # 启动服务
    success, info = await pm.start_backend_service(debug=True)
    if success:
        print(f"启动成功: {info}")
        
        # 等待一段时间
        await asyncio.sleep(5)
        
        # 停止服务
        if await pm.stop_backend_service():
            print("停止成功")
        else:
            print("停止失败")
    else:
        print(f"启动失败: {info}")


if __name__ == "__main__":
    import os
    asyncio.run(test_process_manager())