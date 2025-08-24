"""
量化回测系统 - 统一服务管理器
管理所有相关服务：前端、后端、Electron等
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import subprocess
import requests
import json
import webbrowser
from datetime import datetime
import psutil
import os
import sys
from pathlib import Path

# 导入统一端口配置
try:
    from ports_config import get_backend_port, get_frontend_port, get_backend_url, get_frontend_url
    PORTS_CONFIG_AVAILABLE = True
except ImportError:
    PORTS_CONFIG_AVAILABLE = False
    
# 导入共享配置（保持向后兼容）
try:
    from shared_config import get_config
    SHARED_CONFIG_AVAILABLE = True
except ImportError:
    SHARED_CONFIG_AVAILABLE = False


class UnifiedServiceManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("量化回测系统 - 统一服务管理器")
        self.root.geometry("1000x700")
        
        # 初始化配置
        self.load_shared_config()
        
        self.monitoring = False
        self.setup_ui()
        self.start_monitoring()
        
    def load_shared_config(self):
        """加载共享配置"""
        # 默认配置
        backend_port = 5318
        frontend_port = 5173
        backend_host = "localhost"
        
        # 优先使用统一端口配置
        if PORTS_CONFIG_AVAILABLE:
            try:
                backend_port = get_backend_port()
                frontend_port = get_frontend_port()
                backend_url = get_backend_url()
                frontend_url = get_frontend_url()
                print(f"使用统一端口配置：后端{backend_port}，前端{frontend_port}")
            except Exception as e:
                print(f"警告：无法加载统一端口配置，使用默认值: {e}")
        elif SHARED_CONFIG_AVAILABLE:
            try:
                config = get_config()
                backend_port = config.get('backend.port', 5318)
                frontend_port = config.get('frontend.port', 5173)
                backend_host = config.get('backend.host', 'localhost')
            except Exception as e:
                print(f"警告：无法加载共享配置，使用默认值: {e}")
        
        # 服务配置
        self.services = {
            "backend": {
                "name": "后端API服务",
                "port": backend_port,
                "url": f"http://{backend_host}:{backend_port}" if not PORTS_CONFIG_AVAILABLE else get_backend_url(),
                "health_endpoint": "/healthz",
                "status": "unknown",
                "pid": None,
                "process_name": "main.py"
            },
            "frontend": {
                "name": "前端开发服务器", 
                "port": frontend_port,
                "url": f"http://localhost:{frontend_port}" if not PORTS_CONFIG_AVAILABLE else get_frontend_url(),
                "health_endpoint": "/",
                "status": "unknown", 
                "pid": None,
                "process_name": "npm"
            }
        }
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="量化回测系统 - 统一服务管理器", 
                               font=("Microsoft YaHei", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 服务状态框架
        self.setup_services_frame(main_frame)
        
        # 快速链接框架  
        self.setup_links_frame(main_frame)
        
        # 日志和API测试框架
        self.setup_logs_frame(main_frame)
        
        # 状态栏
        self.status_bar = ttk.Label(main_frame, text="准备就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def setup_services_frame(self, parent):
        """设置服务状态框架"""
        services_frame = ttk.LabelFrame(parent, text="服务状态", padding="10")
        services_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        services_frame.grid_columnconfigure(1, weight=1)
        services_frame.grid_columnconfigure(3, weight=1)
        
        # 后端服务
        ttk.Label(services_frame, text="后端API服务:", font=("Microsoft YaHei", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 20), pady=5)
        
        self.backend_status = ttk.Label(services_frame, text="检查中...", foreground="orange")
        self.backend_status.grid(row=0, column=1, sticky=tk.W)
        
        backend_btn_frame = ttk.Frame(services_frame)
        backend_btn_frame.grid(row=0, column=2, padx=(20, 0))
        
        self.backend_start_btn = ttk.Button(backend_btn_frame, text="启动", 
                                          command=lambda: self.start_backend())
        self.backend_start_btn.pack(side=tk.LEFT, padx=2)
        
        self.backend_stop_btn = ttk.Button(backend_btn_frame, text="停止",
                                         command=lambda: self.stop_backend())
        self.backend_stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.backend_restart_btn = ttk.Button(backend_btn_frame, text="重启",
                                            command=lambda: self.restart_backend())
        self.backend_restart_btn.pack(side=tk.LEFT, padx=2)
        
        # 前端服务
        ttk.Label(services_frame, text="前端开发服务器:", font=("Microsoft YaHei", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 20), pady=5)
        
        self.frontend_status = ttk.Label(services_frame, text="检查中...", foreground="orange")
        self.frontend_status.grid(row=1, column=1, sticky=tk.W)
        
        frontend_btn_frame = ttk.Frame(services_frame)
        frontend_btn_frame.grid(row=1, column=2, padx=(20, 0))
        
        self.frontend_start_btn = ttk.Button(frontend_btn_frame, text="启动",
                                           command=lambda: self.start_frontend())
        self.frontend_start_btn.pack(side=tk.LEFT, padx=2)
        
        self.frontend_stop_btn = ttk.Button(frontend_btn_frame, text="停止",
                                          command=lambda: self.stop_frontend())
        self.frontend_stop_btn.pack(side=tk.LEFT, padx=2)
        
        # 端口信息
        ttk.Label(services_frame, text=f"后端端口: {self.services['backend']['port']}", foreground="blue").grid(
            row=0, column=3, sticky=tk.W, padx=(20, 0))
        ttk.Label(services_frame, text=f"前端端口: {self.services['frontend']['port']}", foreground="blue").grid(
            row=1, column=3, sticky=tk.W, padx=(20, 0))
        
    def setup_links_frame(self, parent):
        """设置快速链接框架"""
        links_frame = ttk.LabelFrame(parent, text="快速链接", padding="10")
        links_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N), padx=(10, 0), pady=(0, 10))
        
        # 前端链接
        ttk.Button(links_frame, text="🌐 打开前端应用", 
                  command=lambda: self.open_url(self.services["frontend"]["url"])).pack(fill=tk.X, pady=2)
        
        # API文档链接
        ttk.Button(links_frame, text="📚 API文档", 
                  command=lambda: self.open_url(f"{self.services['backend']['url']}/docs")).pack(fill=tk.X, pady=2)
        
        # 健康检查
        ttk.Button(links_frame, text="💚 后端健康检查", 
                  command=lambda: self.open_url(f"{self.services['backend']['url']}/healthz")).pack(fill=tk.X, pady=2)
        
        ttk.Separator(links_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # API测试按钮
        ttk.Label(links_frame, text="API测试:", font=("Microsoft YaHei", 9, "bold")).pack(anchor=tk.W)
        
        api_frame = ttk.Frame(links_frame)
        api_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(api_frame, text="数据状态", width=12,
                  command=lambda: self.test_api("/data/status")).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_frame, text="标签列表", width=12,
                  command=lambda: self.test_api("/labels/list")).pack(side=tk.LEFT, padx=2)
        
        api_frame2 = ttk.Frame(links_frame)
        api_frame2.pack(fill=tk.X, pady=2)
        
        ttk.Button(api_frame2, text="策略列表", width=12,
                  command=lambda: self.test_api("/backtest/strategies")).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_frame2, text="清空日志", width=12,
                  command=self.clear_log).pack(side=tk.LEFT, padx=2)
        
    def setup_logs_frame(self, parent):
        """设置日志框架"""
        logs_frame = ttk.LabelFrame(parent, text="服务日志和API响应", padding="10")
        logs_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        logs_frame.grid_rowconfigure(0, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)
        
        # 创建Notebook用于分页显示
        self.notebook = ttk.Notebook(logs_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # API测试日志页
        api_frame = ttk.Frame(self.notebook)
        self.notebook.add(api_frame, text="API测试")
        api_frame.grid_rowconfigure(0, weight=1)
        api_frame.grid_columnconfigure(0, weight=1)
        
        self.api_log = scrolledtext.ScrolledText(api_frame, height=15, font=("Consolas", 9))
        self.api_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self._setup_text_context_menu(self.api_log)
        
        # 后端日志页
        backend_frame = ttk.Frame(self.notebook)
        self.notebook.add(backend_frame, text="后端日志")
        backend_frame.grid_rowconfigure(0, weight=1)
        backend_frame.grid_columnconfigure(0, weight=1)
        
        self.backend_log = scrolledtext.ScrolledText(backend_frame, height=15, font=("Consolas", 9))
        self.backend_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self._setup_text_context_menu(self.backend_log)
        
        # 添加日志控制按钮
        log_control_frame = ttk.Frame(backend_frame)
        log_control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(log_control_frame, text="刷新后端日志", command=self.refresh_backend_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text="清空显示", command=self.clear_backend_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text="复制选中", command=lambda: self._copy_selected_text(self.backend_log)).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text="复制全部", command=lambda: self._copy_all_text(self.backend_log)).pack(side=tk.LEFT, padx=5)
        
    def start_monitoring(self):
        """启动监控线程"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_services, daemon=True)
        monitor_thread.start()
        
    def monitor_services(self):
        """监控所有服务状态"""
        while self.monitoring:
            self.check_all_services()
            time.sleep(3)  # 每3秒检查一次
            
    def check_all_services(self):
        """检查所有服务状态"""
        # 检查后端服务
        self.check_backend_status()
        # 检查前端服务
        self.check_frontend_status()
        # 更新按钮状态
        self.update_button_states()
        
    def check_backend_status(self):
        """检查后端服务状态"""
        try:
            health_url = f"{self.services['backend']['url']}/healthz"
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                self.services["backend"]["status"] = "running"
                port = self.services['backend']['port']
                self.backend_status.config(text=f"🟢 运行中 ({port})", foreground="green")
            else:
                raise requests.RequestException("非200响应")
        except:
            self.services["backend"]["status"] = "stopped"
            self.backend_status.config(text="🔴 已停止", foreground="red")
            
    def check_frontend_status(self):
        """检查前端服务状态"""
        try:
            response = requests.get(self.services["frontend"]["url"], timeout=2)
            # Vite开发服务器通常返回HTML页面
            if response.status_code == 200:
                self.services["frontend"]["status"] = "running"
                port = self.services['frontend']['port']
                self.frontend_status.config(text=f"🟢 运行中 ({port})", foreground="green")
            else:
                raise requests.RequestException("非200响应")
        except:
            self.services["frontend"]["status"] = "stopped"
            self.frontend_status.config(text="🔴 已停止", foreground="red")
            
    def update_button_states(self):
        """更新按钮状态"""
        # 后端按钮
        if self.services["backend"]["status"] == "running":
            self.backend_start_btn.config(state="disabled")
            self.backend_stop_btn.config(state="normal")
            self.backend_restart_btn.config(state="normal")
        else:
            self.backend_start_btn.config(state="normal")
            self.backend_stop_btn.config(state="disabled")
            self.backend_restart_btn.config(state="disabled")
            
        # 前端按钮
        if self.services["frontend"]["status"] == "running":
            self.frontend_start_btn.config(state="disabled") 
            self.frontend_stop_btn.config(state="normal")
        else:
            self.frontend_start_btn.config(state="normal")
            self.frontend_stop_btn.config(state="disabled")
            
    def start_backend(self):
        """启动后端服务"""
        self.log_message("正在启动后端服务...")
        
        def run_start():
            try:
                result = subprocess.run(
                    [sys.executable, "unified_service_manager.py", "start"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    self.log_message("✅ 后端服务启动成功")
                else:
                    self.log_message(f"❌ 后端服务启动失败: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"❌ 启动后端服务时出错: {e}")
                
        threading.Thread(target=run_start, daemon=True).start()
        
    def stop_backend(self):
        """停止后端服务"""
        self.log_message("正在停止后端服务...")
        
        def run_stop():
            try:
                result = subprocess.run(
                    [sys.executable, "unified_service_manager.py", "stop"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    self.log_message("✅ 后端服务停止成功")
                else:
                    self.log_message(f"❌ 后端服务停止失败: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"❌ 停止后端服务时出错: {e}")
                
        threading.Thread(target=run_stop, daemon=True).start()
        
    def restart_backend(self):
        """重启后端服务"""
        self.log_message("正在重启后端服务...")
        
        def run_restart():
            try:
                result = subprocess.run(
                    [sys.executable, "unified_service_manager.py", "restart"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    self.log_message("✅ 后端服务重启成功")
                else:
                    self.log_message(f"❌ 后端服务重启失败: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"❌ 重启后端服务时出错: {e}")
                
        threading.Thread(target=run_restart, daemon=True).start()
        
    def start_frontend(self):
        """启动前端服务"""
        self.log_message("正在启动前端开发服务器...")
        
        def run_start():
            try:
                # 启动前端开发服务器
                process = subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=Path.cwd() / "frontend",
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                
                # 保存PID到服务信息
                self.services["frontend"]["pid"] = process.pid
                
                self.log_message("✅ 前端开发服务器启动命令已执行")
                self.log_message(f"💡 前端服务器PID: {process.pid}")
                self.log_message("💡 前端服务器会在新的控制台窗口中运行")
                
            except Exception as e:
                self.log_message(f"❌ 启动前端服务时出错: {e}")
                
        threading.Thread(target=run_start, daemon=True).start()
        
    def stop_frontend(self):
        """停止前端服务"""
        self.log_message("正在停止前端服务...")
        
        def run_stop():
            try:
                # 优先使用保存的PID
                frontend_pid = self.services["frontend"].get("pid")
                if frontend_pid:
                    try:
                        proc = psutil.Process(frontend_pid)
                        if proc.is_running():
                            proc.terminate()
                            self.log_message(f"✅ 停止前端进程 PID: {frontend_pid}")
                            self.services["frontend"]["pid"] = None
                            return
                    except psutil.NoSuchProcess:
                        self.log_message("⚠️ 保存的前端PID已不存在，尝试查找进程")
                
                # 如果PID方式失败，回退到进程查找
                stopped = False
                frontend_port = str(self.services['frontend']['port'])
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any('vite' in str(cmd).lower() for cmd in cmdline):
                            if any(frontend_port in str(cmd) for cmd in cmdline):
                                proc.terminate()
                                self.log_message(f"✅ 停止前端进程 PID: {proc.info['pid']}")
                                stopped = True
                                break
                    except:
                        continue
                
                if not stopped:
                    self.log_message("⚠️ 未找到前端进程")
                
                # 清理PID记录
                self.services["frontend"]["pid"] = None
                
            except Exception as e:
                self.log_message(f"❌ 停止前端服务时出错: {e}")
                
        threading.Thread(target=run_stop, daemon=True).start()
        
    def open_url(self, url):
        """打开URL"""
        try:
            webbrowser.open(url)
            self.log_message(f"🌐 已打开链接: {url}")
        except Exception as e:
            self.log_message(f"❌ 打开链接失败: {e}")
            
    def test_api(self, endpoint):
        """测试API端点"""
        self.log_message(f"🔄 正在测试API: {endpoint}")
        
        def run_test():
            try:
                url = f"{self.services['backend']['url']}{endpoint}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        formatted = json.dumps(data, indent=2, ensure_ascii=False)
                        self.log_message(f"✅ API测试成功 {endpoint}:")
                        self.log_message(formatted)
                    except json.JSONDecodeError:
                        self.log_message(f"✅ API响应 {endpoint}: {response.text[:200]}...")
                else:
                    self.log_message(f"❌ API测试失败 {endpoint}: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_message(f"❌ API测试出错 {endpoint}: {e}")
                
        threading.Thread(target=run_test, daemon=True).start()
        
    def refresh_backend_log(self):
        """刷新后端日志"""
        self.log_message("🔄 正在获取后端日志...")
        
        def run_refresh():
            try:
                # 简化的日志显示
                self.backend_log.delete(1.0, tk.END)
                self.backend_log.insert(tk.END, "📋 日志功能将在未来版本中完善\n")
                self.backend_log.insert(tk.END, "提示: 可以通过命令行 'python unified_service_manager.py logs' 查看日志\n")
                self.log_message("📋 日志显示已更新")
                    
            except Exception as e:
                self.log_message(f"❌ 刷新后端日志时出错: {e}")
                
        threading.Thread(target=run_refresh, daemon=True).start()
        
    def clear_log(self):
        """清空API日志"""
        self.api_log.delete(1.0, tk.END)
        self.log_message("🧹 API日志已清空")
        
    def clear_backend_log(self):
        """清空后端日志显示"""
        self.backend_log.delete(1.0, tk.END)
        self.log_message("🧹 后端日志显示已清空")
        
    def log_message(self, message):
        """记录消息到API日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.api_log.insert(tk.END, log_entry)
        self.api_log.see(tk.END)
        
        # 更新状态栏
        self.status_bar.config(text=f"最后操作: {message}")
        
    def run(self):
        """运行GUI"""
        self.log_message("🚀 统一服务管理器启动")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """关闭时清理"""
        self.monitoring = False
        self.root.destroy()
    
    def _setup_text_context_menu(self, text_widget):
        """为文本组件设置右键菜单"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="复制选中", command=lambda: self._copy_selected_text(text_widget))
        context_menu.add_command(label="复制全部", command=lambda: self._copy_all_text(text_widget))
        context_menu.add_command(label="全选", command=lambda: self._select_all_text(text_widget))
        context_menu.add_separator()
        context_menu.add_command(label="清空", command=lambda: text_widget.delete(1.0, tk.END))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
            finally:
                context_menu.grab_release()
        
        text_widget.bind("<Button-3>", show_context_menu)  # 右键点击
    
    def _copy_selected_text(self, text_widget):
        """复制选中的文本到剪贴板"""
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                self.log_message("📋 已复制选中文本")
            else:
                self.log_message("⚠️ 没有选中文本")
        except tk.TclError:
            self.log_message("⚠️ 没有选中文本")
    
    def _copy_all_text(self, text_widget):
        """复制全部文本到剪贴板"""
        try:
            all_text = text_widget.get(1.0, tk.END)
            if all_text.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(all_text)
                self.log_message("📋 已复制全部文本")
            else:
                self.log_message("⚠️ 没有文本可复制")
        except Exception as e:
            self.log_message(f"❌ 复制失败: {e}")
    
    def _select_all_text(self, text_widget):
        """全选文本"""
        try:
            text_widget.tag_add(tk.SEL, "1.0", tk.END)
            text_widget.mark_set(tk.INSERT, "1.0")
            text_widget.see(tk.INSERT)
            self.log_message("✅ 已全选文本")
        except Exception as e:
            self.log_message(f"❌ 全选失败: {e}")


def run_command_line():
    """命令行模式运行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='量化回测系统服务管理工具')
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
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_parser.add_argument('--show', action='store_true', help='显示当前配置')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建一个简化的服务管理器用于命令行操作
    class CLIServiceManager:
        def __init__(self):
            self.project_root = Path(__file__).parent
            self.backend_dir = self.project_root / "backend"
            self.pid_file = self.project_root / ".service.pid"
            
        def get_service_pid(self, service_name):
            """获取服务PID"""
            if not self.pid_file.exists():
                return None
            try:
                with open(self.pid_file, 'r') as f:
                    data = json.load(f)
                return data.get(service_name)
            except:
                return None
                
        def is_process_running(self, pid):
            """检查进程是否运行"""
            try:
                return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
            except:
                return False
                
        def start_backend(self):
            """启动后端服务"""
            print("🚀 启动后端服务...")
            try:
                cmd = [sys.executable, str(self.backend_dir / "app" / "main.py"), "--port", "5318"]
                process = subprocess.Popen(cmd, cwd=str(self.project_root))
                
                # 保存PID
                pid_data = {}
                if self.pid_file.exists():
                    try:
                        with open(self.pid_file, 'r') as f:
                            pid_data = json.load(f)
                    except:
                        pass
                
                pid_data['backend'] = process.pid
                with open(self.pid_file, 'w') as f:
                    json.dump(pid_data, f)
                
                print(f"✅ 后端服务启动成功 (PID: {process.pid})")
                print(f"📍 服务地址: http://127.0.0.1:5318")
                return True
            except Exception as e:
                print(f"❌ 启动失败: {e}")
                return False
                
        def stop_backend(self):
            """停止后端服务"""
            pid = self.get_service_pid('backend')
            if not pid:
                print("⚠️ 后端服务未运行")
                return True
                
            if not self.is_process_running(pid):
                print("⚠️ 后端服务进程已停止")
                return True
                
            try:
                psutil.Process(pid).terminate()
                time.sleep(2)
                if self.is_process_running(pid):
                    psutil.Process(pid).kill()
                print("✅ 后端服务已停止")
                return True
            except Exception as e:
                print(f"❌ 停止失败: {e}")
                return False
                
        def show_status(self):
            """显示服务状态"""
            print("📊 系统状态")
            print("=" * 50)
            
            # 检查后端状态
            backend_pid = self.get_service_pid('backend')
            if backend_pid and self.is_process_running(backend_pid):
                print(f"✅ 后端服务: 运行中 (PID: {backend_pid})")
                print(f"📍 服务地址: http://127.0.0.1:5318")
            else:
                print("❌ 后端服务: 已停止")
                
            print(f"🕐 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    manager = CLIServiceManager()
    
    try:
        if args.command == 'status':
            manager.show_status()
        elif args.command == 'start':
            manager.start_backend()
        elif args.command == 'stop':
            manager.stop_backend()
        elif args.command == 'restart':
            print("🔄 重启后端服务...")
            manager.stop_backend()
            time.sleep(2)
            manager.start_backend()
        elif args.command == 'logs':
            print("📋 查看日志功能需要在GUI模式下使用")
        elif args.command == 'config':
            if args.show:
                print("📋 当前配置:")
                print("  后端端口: 5318")
                print("  前端端口: 5173")
            else:
                print("📋 配置修改功能需要在GUI模式下使用")
    except KeyboardInterrupt:
        print("\n⚠️ 操作被取消")
    except Exception as e:
        print(f"❌ 操作失败: {e}")


if __name__ == "__main__":
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        run_command_line()
    else:
        # GUI模式
        app = UnifiedServiceManager()
        app.run()