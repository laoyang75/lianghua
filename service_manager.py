#!/usr/bin/env python3
"""
量化回测系统 - 服务管理工具
独立的命令行工具，用于管理后台服务的启动、停止、重启
"""

import argparse
import json
import os
import psutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# 导入共享配置
try:
    from shared_config import get_config
    SHARED_CONFIG_AVAILABLE = True
except ImportError:
    SHARED_CONFIG_AVAILABLE = False

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(text: str, color: str = Colors.WHITE):
    """带颜色的打印输出"""
    print(f"{color}{text}{Colors.END}")

def print_header(text: str):
    """打印标题"""
    print_colored(f"\n{Colors.BOLD}{'='*50}", Colors.CYAN)
    print_colored(f"{Colors.BOLD}{text.center(50)}", Colors.CYAN)
    print_colored(f"{Colors.BOLD}{'='*50}", Colors.CYAN)

def print_success(text: str):
    """打印成功信息"""
    print_colored(f"[OK] {text}", Colors.GREEN)

def print_error(text: str):
    """打印错误信息"""
    print_colored(f"[ERROR] {text}", Colors.RED)

def print_warning(text: str):
    """打印警告信息"""
    print_colored(f"[WARN] {text}", Colors.YELLOW)

def print_info(text: str):
    """打印信息"""
    print_colored(f"[INFO] {text}", Colors.BLUE)


class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.pid_file = self.project_root / ".service.pid"
        self.config_file = self.project_root / "service_config.json"
        
        # 默认配置
        self.config = {
            "backend": {
                "port": 5318,
                "host": "127.0.0.1",
                "debug": False,
                "auto_restart": True
            },
            "frontend": {
                "port": 5182,
                "auto_start": False  # 前端通常手动启动
            }
        }
        
        self.load_config()
        self.monitoring = False
        self.monitor_thread = None
        
        # 如果有共享配置，则同步配置
        if SHARED_CONFIG_AVAILABLE:
            self.sync_with_shared_config()
    
    def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                print_info("已加载配置文件")
            except Exception as e:
                print_warning(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print_success("配置已保存")
        except Exception as e:
            print_error(f"保存配置失败: {e}")

    def sync_with_shared_config(self):
        """与共享配置同步"""
        try:
            shared_config = get_config()
            
            # 同步后端配置
            backend_config = shared_config.backend
            self.config['backend'].update({
                'host': backend_config.get('host', self.config['backend']['host']),
                'port': backend_config.get('port', self.config['backend']['port']),
                'debug': backend_config.get('debug', self.config['backend']['debug']),
                'auto_restart': backend_config.get('auto_restart', self.config['backend']['auto_restart'])
            })
            
            # 同步前端配置  
            frontend_config = shared_config.frontend
            self.config['frontend'].update({
                'port': frontend_config.get('port', self.config['frontend']['port']),
                'auto_start': frontend_config.get('auto_start', self.config['frontend']['auto_start'])
            })
            
            print_info("已同步共享配置")
            
        except Exception as e:
            print_warning(f"同步共享配置失败: {e}")
    
    def get_service_pid(self, service_name: str) -> Optional[int]:
        """获取服务进程ID"""
        try:
            if not self.pid_file.exists():
                return None
            
            with open(self.pid_file, 'r') as f:
                pids = json.load(f)
                return pids.get(service_name)
        except Exception:
            return None
    
    def save_service_pid(self, service_name: str, pid: int):
        """保存服务进程ID"""
        try:
            pids = {}
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    pids = json.load(f)
            
            pids[service_name] = pid
            
            with open(self.pid_file, 'w') as f:
                json.dump(pids, f)
        except Exception as e:
            print_error(f"保存PID失败: {e}")
    
    def remove_service_pid(self, service_name: str):
        """移除服务进程ID记录"""
        try:
            if not self.pid_file.exists():
                return
            
            with open(self.pid_file, 'r') as f:
                pids = json.load(f)
            
            if service_name in pids:
                del pids[service_name]
                
                if pids:
                    with open(self.pid_file, 'w') as f:
                        json.dump(pids, f)
                else:
                    self.pid_file.unlink()
        except Exception as e:
            print_error(f"移除PID记录失败: {e}")
    
    def is_process_running(self, pid: int) -> bool:
        """检查进程是否运行"""
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
        except Exception:
            return False

    def is_backend_process_running(self, pid: int) -> bool:
        """检查指定PID是否为后端服务进程"""
        try:
            if not psutil.pid_exists(pid):
                self.remove_service_pid('backend')  # 清理失效记录
                return False
            
            proc = psutil.Process(pid)
            if not proc.is_running():
                self.remove_service_pid('backend')  # 清理失效记录
                return False
            
            # 检查进程命令行是否包含后端服务特征
            cmdline = proc.cmdline()
            is_backend = any('main.py' in arg for arg in cmdline) and \
                        any('backend' in arg or 'app' in arg for arg in cmdline)
            
            if not is_backend:
                print_warning(f"PID {pid} 不是后端服务进程，清理记录")
                self.remove_service_pid('backend')  # 清理误记录
                return False
                
            return True
        except Exception:
            self.remove_service_pid('backend')  # 清理异常记录
            return False

    def cleanup_stale_pid_records(self):
        """清理所有失效的PID记录"""
        try:
            if not self.pid_file.exists():
                return
                
            with open(self.pid_file, 'r') as f:
                pids = json.load(f)
            
            stale_services = []
            for service_name, pid in pids.items():
                if not self.is_process_running(pid):
                    stale_services.append(service_name)
            
            for service_name in stale_services:
                print_info(f"清理失效的PID记录: {service_name}")
                self.remove_service_pid(service_name)
                
        except Exception as e:
            print_error(f"清理PID记录失败: {e}")

    def wait_for_service_ready(self, host: str, port: int, timeout: int = 30) -> bool:
        """等待服务就绪，通过健康检查确认"""
        import requests
        from urllib.parse import urljoin
        
        base_url = f"http://{host}:{port}"
        health_url = urljoin(base_url, "/healthz")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 首先检查端口是否开放
                if not self.is_port_available(port, host):
                    # 端口已开放，尝试健康检查
                    response = requests.get(health_url, timeout=2)
                    if response.status_code == 200:
                        print_success("服务健康检查通过")
                        return True
                    else:
                        print_info(f"健康检查响应: {response.status_code}")
                else:
                    print_info(f"等待端口 {port} 开放...")
                    
            except requests.RequestException as e:
                print_info(f"健康检查连接失败: {e}")
            
            time.sleep(1)
        
        print_error(f"服务在 {timeout} 秒内未就绪")
        return False

    def start_monitoring(self):
        """启动服务监控"""
        if not self.config['backend'].get('auto_restart', False):
            return
            
        if self.monitoring:
            return
            
        self.monitoring = True
        import threading
        self.monitor_thread = threading.Thread(target=self._monitor_service, daemon=True)
        self.monitor_thread.start()
        print_info("已启动服务监控")

    def stop_monitoring(self):
        """停止服务监控"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        print_info("已停止服务监控")

    def _monitor_service(self):
        """服务监控循环"""
        while self.monitoring:
            try:
                time.sleep(10)  # 每10秒检查一次
                
                if not self.monitoring:
                    break
                
                # 检查后端服务
                pid = self.get_service_pid('backend')
                if pid and not self.is_backend_process_running(pid):
                    print_warning("检测到后端服务异常退出，尝试自动重启...")
                    if self.start_backend():
                        print_success("后端服务自动重启成功")
                    else:
                        print_error("后端服务自动重启失败")
                        
            except Exception as e:
                print_error(f"监控服务异常: {e}")
                time.sleep(5)
    
    def kill_process(self, pid: int, force: bool = False):
        """终止进程"""
        try:
            if not self.is_process_running(pid):
                return True
            
            process = psutil.Process(pid)
            
            if force:
                process.kill()
            else:
                process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
                return True
            except psutil.TimeoutExpired:
                if not force:
                    print_warning("正常终止超时，强制终止进程...")
                    return self.kill_process(pid, force=True)
                return False
                
        except psutil.NoSuchProcess:
            return True
        except Exception as e:
            print_error(f"终止进程失败: {e}")
            return False
    
    def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """检查端口是否可用"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result != 0  # 0表示连接成功，即端口被占用
        except Exception:
            return False

    def find_available_port(self, start_port: int = 5318, max_attempts: int = 100) -> Optional[int]:
        """寻找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port):
                return port
        return None

    def start_backend(self) -> bool:
        """启动后端服务"""
        # 检查是否已经运行
        pid = self.get_service_pid('backend')
        if pid and self.is_backend_process_running(pid):
            print_warning("后端服务已在运行")
            return True

        # 检查端口占用
        config = self.config['backend']
        port = config['port']
        if not self.is_port_available(port, config['host']):
            print_error(f"端口 {port} 被占用")
            # 尝试寻找可用端口
            available_port = self.find_available_port(port)
            if available_port:
                print_info(f"使用替代端口: {available_port}")
                config['port'] = available_port
                self.save_config()  # 保存新的端口配置
            else:
                print_error("无法找到可用端口")
                return False
        
        # 检查Python环境
        if not self.backend_dir.exists():
            print_error("后端目录不存在")
            return False
        
        if not (self.backend_dir / "app" / "main.py").exists():
            print_error("后端主程序不存在")
            return False
        
        try:
            # 构建启动命令
            config = self.config['backend']
            cmd = [
                sys.executable,
                str(self.backend_dir / "app" / "main.py"),
                "--port", str(config['port']),
                "--host", config['host']
            ]
            
            if config['debug']:
                cmd.append("--debug")
            
            print_info(f"启动后端服务: {' '.join(cmd)}")
            
            # 创建日志文件路径
            log_dir = self.get_log_dir()
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"backend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            
            # 启动进程 - 将输出重定向到日志文件，避免管道阻塞
            with open(log_file, 'w', encoding='utf-8') as logf:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.project_root),
                    stdout=logf,
                    stderr=subprocess.STDOUT,  # 合并stderr到stdout
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
            
            print_info(f"后端服务日志: {log_file}")
            
            # 等待服务启动并进行健康检查
            if self.wait_for_service_ready(config['host'], config['port'], timeout=30):
                if process.poll() is None:  # 确保进程还在运行
                    self.save_service_pid('backend', process.pid)
                    print_success(f"后端服务启动成功 (PID: {process.pid})")
                    print_info(f"服务地址: http://{config['host']}:{config['port']}")
                    return True
                else:
                    print_error("进程意外退出")
                    return False
            else:
                print_error("后端服务健康检查失败")
                if process.poll() is None:
                    self.kill_process(process.pid, force=True)
                return False
                
        except Exception as e:
            print_error(f"启动后端服务失败: {e}")
            return False
    
    def stop_backend(self) -> bool:
        """停止后端服务"""
        pid = self.get_service_pid('backend')
        if not pid:
            print_warning("后端服务未运行")
            return True
        
        if not self.is_process_running(pid):
            self.remove_service_pid('backend')
            print_warning("后端服务进程已停止")
            return True
        
        print_info(f"正在停止后端服务 (PID: {pid})...")
        
        if self.kill_process(pid):
            self.remove_service_pid('backend')
            print_success("后端服务已停止")
            return True
        else:
            print_error("停止后端服务失败")
            return False
    
    def restart_backend(self) -> bool:
        """重启后端服务"""
        print_info("重启后端服务...")
        self.stop_backend()
        time.sleep(2)
        return self.start_backend()
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            'backend': {'running': False, 'pid': None, 'port': None},
            'system': {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            }
        }
        
        # 检查后端状态
        backend_pid = self.get_service_pid('backend')
        if backend_pid and self.is_process_running(backend_pid):
            status['backend']['running'] = True
            status['backend']['pid'] = backend_pid
            status['backend']['port'] = self.config['backend']['port']
        
        return status
    
    def show_status(self):
        """显示服务状态"""
        print_header("服务状态")
        
        status = self.get_service_status()
        
        # 显示系统信息
        print_info(f"系统时间: {status['system']['time']}")
        print_info(f"Python版本: {status['system']['python_version']}")
        print()
        
        # 显示后端状态
        backend = status['backend']
        if backend['running']:
            print_success(f"后端服务: 运行中 (PID: {backend['pid']}, 端口: {backend['port']})")
        else:
            print_error("后端服务: 未运行")
        
        print()
    
    def get_log_dir(self) -> Path:
        """获取跨平台日志目录"""
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', str(self.project_root)))
            log_dir = base_dir / 'QuantBacktest' / 'logs'
        elif sys.platform == 'darwin':  # macOS
            base_dir = Path.home() / 'Library' / 'Logs'
            log_dir = base_dir / 'QuantBacktest'
        else:  # Linux/Unix
            base_dir = Path.home() / '.local' / 'share'
            log_dir = base_dir / 'QuantBacktest' / 'logs'
        
        return log_dir

    def show_logs(self, service: str = 'backend', lines: int = 50):
        """显示日志"""
        print_header(f"{service.upper()} 服务日志")
        
        log_dir = self.get_log_dir()
        if not log_dir.exists():
            print_error("日志目录不存在")
            return
        
        # 查找最新的日志文件
        log_files = list(log_dir.glob("backend_*.log"))
        if not log_files:
            print_error("未找到日志文件")
            return
        
        latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                for line in recent_lines:
                    line = line.strip()
                    if 'ERROR' in line:
                        print_colored(line, Colors.RED)
                    elif 'WARNING' in line:
                        print_colored(line, Colors.YELLOW)
                    elif 'INFO' in line:
                        print_colored(line, Colors.WHITE)
                    else:
                        print(line)
        except Exception as e:
            print_error(f"读取日志失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="量化回测系统服务管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
命令示例:
  %(prog)s status          # 查看服务状态
  %(prog)s start           # 启动后端服务
  %(prog)s stop            # 停止后端服务  
  %(prog)s restart         # 重启后端服务
  %(prog)s logs            # 查看日志
  %(prog)s logs --lines 100  # 查看最近100行日志
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    subparsers.add_parser('status', help='查看服务状态')
    
    # start 命令
    subparsers.add_parser('start', help='启动后端服务')
    
    # stop 命令
    subparsers.add_parser('stop', help='停止后端服务')
    
    # restart 命令
    subparsers.add_parser('restart', help='重启后端服务')
    
    # logs 命令
    logs_parser = subparsers.add_parser('logs', help='查看服务日志')
    logs_parser.add_argument('--lines', type=int, default=50, help='显示的行数')
    logs_parser.add_argument('--service', default='backend', help='服务名称')
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_parser.add_argument('--port', type=int, help='设置后端端口')
    config_parser.add_argument('--debug', action='store_true', help='启用调试模式')
    config_parser.add_argument('--show', action='store_true', help='显示当前配置')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 检查依赖
    try:
        import psutil
    except ImportError:
        print_error("缺少 psutil 依赖，请运行: pip install psutil")
        return
    
    manager = ServiceManager()
    
    try:
        if args.command == 'status':
            manager.show_status()
            
        elif args.command == 'start':
            print_header("启动服务")
            if manager.start_backend():
                manager.start_monitoring()  # 启动监控
                print_success("服务启动完成")
            else:
                print_error("服务启动失败")
                sys.exit(1)
                
        elif args.command == 'stop':
            print_header("停止服务")
            if manager.stop_backend():
                print_success("服务停止完成")
            else:
                print_error("服务停止失败")
                sys.exit(1)
                
        elif args.command == 'restart':
            print_header("重启服务")
            if manager.restart_backend():
                print_success("服务重启完成")
            else:
                print_error("服务重启失败")
                sys.exit(1)
                
        elif args.command == 'logs':
            manager.show_logs(args.service, args.lines)
            
        elif args.command == 'config':
            if args.show:
                print_header("当前配置")
                print(json.dumps(manager.config, indent=2, ensure_ascii=False))
            else:
                changed = False
                if args.port:
                    manager.config['backend']['port'] = args.port
                    print_success(f"后端端口设置为: {args.port}")
                    changed = True
                
                if args.debug:
                    manager.config['backend']['debug'] = True
                    print_success("调试模式已启用")
                    changed = True
                
                if changed:
                    manager.save_config()
                else:
                    print_info("没有配置更改")
                    
    except KeyboardInterrupt:
        print_warning("\n操作被取消")
    except Exception as e:
        print_error(f"操作失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()