"""
量化回测系统 - 服务管理GUI工具
基于tkinter的桌面应用，用于管理后端服务和监控API状态
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import subprocess
import requests
import json
from datetime import datetime
import psutil
import os
import sys
from pathlib import Path


class ServiceManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("量化回测系统 - 服务管理器")
        self.root.geometry("800x600")
        
        # 设置图标（如果存在）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
            
        # 服务状态
        self.service_pid = None
        self.service_port = 5318
        self.service_status = "stopped"
        self.monitoring = False
        
        self.setup_ui()
        self.start_monitoring()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="量化回测系统服务管理器", 
                               font=("Microsoft YaHei", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 服务状态框架
        status_frame = ttk.LabelFrame(main_frame, text="服务状态", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.grid_columnconfigure(1, weight=1)
        
        # 状态指示器
        ttk.Label(status_frame, text="服务状态:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_label = ttk.Label(status_frame, text="检查中...", foreground="orange")
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="端口:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.port_label = ttk.Label(status_frame, text=f"{self.service_port}")
        self.port_label.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="PID:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.pid_label = ttk.Label(status_frame, text="N/A")
        self.pid_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="运行时间:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.uptime_label = ttk.Label(status_frame, text="N/A")
        self.uptime_label.grid(row=3, column=1, sticky=tk.W)
        
        # 控制按钮框架
        control_frame = ttk.Frame(status_frame)
        control_frame.grid(row=0, column=2, rowspan=4, padx=(20, 0))
        
        self.start_btn = ttk.Button(control_frame, text="启动服务", command=self.start_service)
        self.start_btn.grid(row=0, column=0, pady=2, sticky=tk.W+tk.E)
        
        self.stop_btn = ttk.Button(control_frame, text="停止服务", command=self.stop_service)
        self.stop_btn.grid(row=1, column=0, pady=2, sticky=tk.W+tk.E)
        
        self.restart_btn = ttk.Button(control_frame, text="重启服务", command=self.restart_service)
        self.restart_btn.grid(row=2, column=0, pady=2, sticky=tk.W+tk.E)
        
        ttk.Button(control_frame, text="刷新状态", command=self.check_service_status).grid(row=3, column=0, pady=2, sticky=tk.W+tk.E)
        
        # API测试框架
        api_frame = ttk.LabelFrame(main_frame, text="API测试", padding="10")
        api_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        api_frame.grid_rowconfigure(1, weight=1)
        api_frame.grid_columnconfigure(0, weight=1)
        
        # API测试按钮
        api_btn_frame = ttk.Frame(api_frame)
        api_btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(api_btn_frame, text="健康检查", command=self.test_health).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_btn_frame, text="数据状态", command=self.test_data_status).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_btn_frame, text="标签列表", command=self.test_labels).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_btn_frame, text="策略列表", command=self.test_strategies).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_btn_frame, text="清空日志", command=self.clear_api_log).pack(side=tk.LEFT, padx=(0, 5))
        
        # API响应日志
        self.api_log = scrolledtext.ScrolledText(api_frame, height=15, font=("Consolas", 9))
        self.api_log.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 服务日志框架
        log_frame = ttk.LabelFrame(main_frame, text="服务日志", padding="10")
        log_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(log_btn_frame, text="查看日志", command=self.view_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_btn_frame, text="清空显示", command=self.clear_log_display).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_btn_frame, text="自动滚动", command=self.toggle_auto_scroll).pack(side=tk.LEFT, padx=(0, 5))
        
        # 服务日志显示
        self.log_display = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9))
        self.log_display.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.auto_scroll = True
        
        # 状态栏
        self.status_bar = ttk.Label(main_frame, text="准备就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def log_message(self, message, level="INFO"):
        """记录消息到API日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.api_log.insert(tk.END, log_entry)
        if self.auto_scroll:
            self.api_log.see(tk.END)
            
        # 更新状态栏
        self.status_bar.config(text=f"最后操作: {message}")
        
    def start_monitoring(self):
        """启动监控线程"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_service, daemon=True)
        monitor_thread.start()
        
    def monitor_service(self):
        """监控服务状态"""
        while self.monitoring:
            self.check_service_status()
            time.sleep(5)  # 每5秒检查一次
            
    def check_service_status(self):
        """检查服务状态"""
        try:
            # 检查健康端点
            response = requests.get(f"http://localhost:{self.service_port}/healthz", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.service_status = "running"
                self.status_label.config(text="运行中", foreground="green")
                
                # 更新运行时间
                uptime = data.get('uptime', 0)
                uptime_str = self.format_uptime(uptime)
                self.uptime_label.config(text=uptime_str)
                
                # 查找PID
                self.find_service_pid()
                
            else:
                raise requests.RequestException("非200响应")
                
        except requests.RequestException:
            self.service_status = "stopped"
            self.status_label.config(text="已停止", foreground="red")
            self.uptime_label.config(text="N/A")
            self.pid_label.config(text="N/A")
            self.service_pid = None
            
        # 更新按钮状态
        self.update_button_states()
        
    def find_service_pid(self):
        """查找服务进程PID"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('main.py' in cmd for cmd in cmdline):
                    if any(str(self.service_port) in cmd for cmd in cmdline):
                        self.service_pid = proc.info['pid']
                        self.pid_label.config(text=str(self.service_pid))
                        return
        except:
            pass
            
    def format_uptime(self, seconds):
        """格式化运行时间"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def update_button_states(self):
        """更新按钮状态"""
        if self.service_status == "running":
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.restart_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.restart_btn.config(state="disabled")
            
    def start_service(self):
        """启动服务"""
        self.log_message("正在启动服务...")
        
        def run_start():
            try:
                result = subprocess.run(
                    [sys.executable, "service_manager.py", "start"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    self.log_message("服务启动成功", "SUCCESS")
                else:
                    self.log_message(f"服务启动失败: {result.stderr}", "ERROR")
                    
            except Exception as e:
                self.log_message(f"启动服务时出错: {e}", "ERROR")
                
        threading.Thread(target=run_start, daemon=True).start()
        
    def stop_service(self):
        """停止服务"""
        self.log_message("正在停止服务...")
        
        def run_stop():
            try:
                result = subprocess.run(
                    [sys.executable, "service_manager.py", "stop"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    self.log_message("服务停止成功", "SUCCESS")
                else:
                    self.log_message(f"服务停止失败: {result.stderr}", "ERROR")
                    
            except Exception as e:
                self.log_message(f"停止服务时出错: {e}", "ERROR")
                
        threading.Thread(target=run_stop, daemon=True).start()
        
    def restart_service(self):
        """重启服务"""
        self.log_message("正在重启服务...")
        
        def run_restart():
            try:
                result = subprocess.run(
                    [sys.executable, "service_manager.py", "restart"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    self.log_message("服务重启成功", "SUCCESS")
                else:
                    self.log_message(f"服务重启失败: {result.stderr}", "ERROR")
                    
            except Exception as e:
                self.log_message(f"重启服务时出错: {e}", "ERROR")
                
        threading.Thread(target=run_restart, daemon=True).start()
        
    def test_health(self):
        """测试健康检查API"""
        self.log_message("正在测试健康检查API...")
        
        def run_test():
            try:
                response = requests.get(f"http://localhost:{self.service_port}/healthz", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    self.log_message(f"健康检查成功:\n{formatted}", "SUCCESS")
                else:
                    self.log_message(f"健康检查失败: HTTP {response.status_code}", "ERROR")
            except Exception as e:
                self.log_message(f"健康检查出错: {e}", "ERROR")
                
        threading.Thread(target=run_test, daemon=True).start()
        
    def test_data_status(self):
        """测试数据状态API"""
        self.log_message("正在测试数据状态API...")
        
        def run_test():
            try:
                response = requests.get(f"http://localhost:{self.service_port}/data/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    self.log_message(f"数据状态查询成功:\n{formatted}", "SUCCESS")
                else:
                    self.log_message(f"数据状态查询失败: HTTP {response.status_code}", "ERROR")
            except Exception as e:
                self.log_message(f"数据状态查询出错: {e}", "ERROR")
                
        threading.Thread(target=run_test, daemon=True).start()
        
    def test_labels(self):
        """测试标签列表API"""
        self.log_message("正在测试标签列表API...")
        
        def run_test():
            try:
                response = requests.get(f"http://localhost:{self.service_port}/labels/list", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    self.log_message(f"标签列表查询成功:\n{formatted}", "SUCCESS")
                else:
                    self.log_message(f"标签列表查询失败: HTTP {response.status_code}", "ERROR")
            except Exception as e:
                self.log_message(f"标签列表查询出错: {e}", "ERROR")
                
        threading.Thread(target=run_test, daemon=True).start()
        
    def test_strategies(self):
        """测试策略列表API"""
        self.log_message("正在测试策略列表API...")
        
        def run_test():
            try:
                response = requests.get(f"http://localhost:{self.service_port}/backtest/strategies", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    self.log_message(f"策略列表查询成功:\n{formatted}", "SUCCESS")
                else:
                    self.log_message(f"策略列表查询失败: HTTP {response.status_code}", "ERROR")
            except Exception as e:
                self.log_message(f"策略列表查询出错: {e}", "ERROR")
                
        threading.Thread(target=run_test, daemon=True).start()
        
    def view_logs(self):
        """查看服务日志"""
        self.log_message("正在获取服务日志...")
        
        def run_view():
            try:
                result = subprocess.run(
                    [sys.executable, "service_manager.py", "logs", "--lines", "50"],
                    capture_output=True, text=True, cwd=Path.cwd()
                )
                
                if result.returncode == 0:
                    # 清空显示并添加新日志
                    self.log_display.delete(1.0, tk.END)
                    self.log_display.insert(tk.END, result.stdout)
                    if self.auto_scroll:
                        self.log_display.see(tk.END)
                    self.log_message("日志获取成功", "SUCCESS")
                else:
                    self.log_message(f"日志获取失败: {result.stderr}", "ERROR")
                    
            except Exception as e:
                self.log_message(f"获取日志时出错: {e}", "ERROR")
                
        threading.Thread(target=run_view, daemon=True).start()
        
    def clear_api_log(self):
        """清空API日志"""
        self.api_log.delete(1.0, tk.END)
        self.log_message("API日志已清空")
        
    def clear_log_display(self):
        """清空日志显示"""
        self.log_display.delete(1.0, tk.END)
        self.log_message("服务日志显示已清空")
        
    def toggle_auto_scroll(self):
        """切换自动滚动"""
        self.auto_scroll = not self.auto_scroll
        status = "开启" if self.auto_scroll else "关闭"
        self.log_message(f"自动滚动已{status}")
        
    def run(self):
        """运行GUI"""
        self.log_message("服务管理器启动")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """关闭时清理"""
        self.monitoring = False
        self.root.destroy()


if __name__ == "__main__":
    # 检查是否在正确的目录
    if not os.path.exists("service_manager.py"):
        messagebox.showerror("错误", "未找到 service_manager.py，请在项目根目录运行此程序")
        sys.exit(1)
        
    app = ServiceManagerGUI()
    app.run()