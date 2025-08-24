#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化回测系统 - 服务管理器GUI
基于tkinter的图形界面服务控制台
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import subprocess
import json
import os
import sys
import requests
import psutil
from datetime import datetime
import queue
from ports_config import get_backend_port, get_frontend_port, get_backend_url, get_frontend_url, ports_config


class ServiceManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("量化回测系统 - 服务管理器")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 后端服务状态
        self.backend_pid = None
        self.backend_port = get_backend_port()
        self.backend_status = "stopped"
        self.backend_process = None
        
        # 前端服务状态
        self.frontend_pid = None
        self.frontend_port = get_frontend_port()
        self.frontend_status = "stopped"
        self.frontend_process = None
        
        # 日志队列和存储
        self.log_queue = queue.Queue()
        self.backend_logs = []
        self.frontend_logs = []
        self.system_logs = []
        self.current_log_tab = "system"  # system, backend, frontend
        
        # 创建界面
        self.create_widgets()
        
        # 启动状态更新线程
        self.status_thread = threading.Thread(target=self.status_update_loop, daemon=True)
        self.status_thread.start()
        
        # 启动日志处理线程
        self.log_thread = threading.Thread(target=self.log_process_loop, daemon=True)
        self.log_thread.start()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="量化回测系统服务管理器", 
                               font=('Microsoft YaHei', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 服务状态框架
        status_frame = ttk.LabelFrame(main_frame, text="服务状态", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(3, weight=1)
        
        # 后端服务状态
        ttk.Label(status_frame, text="后端服务:", font=('Microsoft YaHei', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(status_frame, text="状态:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_status_label = ttk.Label(status_frame, text="检查中...", foreground="orange")
        self.backend_status_label.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="端口:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_port_label = ttk.Label(status_frame, text=str(self.backend_port))
        self.backend_port_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="PID:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_pid_label = ttk.Label(status_frame, text="--")
        self.backend_pid_label.grid(row=3, column=1, sticky=tk.W)
        
        # 前端服务状态
        ttk.Label(status_frame, text="前端服务:", font=('Microsoft YaHei', 9, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        
        ttk.Label(status_frame, text="状态:").grid(row=1, column=2, sticky=tk.W, padx=(20, 10))
        self.frontend_status_label = ttk.Label(status_frame, text="检查中...", foreground="orange")
        self.frontend_status_label.grid(row=1, column=3, sticky=tk.W)
        
        ttk.Label(status_frame, text="端口:").grid(row=2, column=2, sticky=tk.W, padx=(20, 10))
        self.frontend_port_label = ttk.Label(status_frame, text=str(self.frontend_port))
        self.frontend_port_label.grid(row=2, column=3, sticky=tk.W)
        
        ttk.Label(status_frame, text="PID:").grid(row=3, column=2, sticky=tk.W, padx=(20, 10))
        self.frontend_pid_label = ttk.Label(status_frame, text="--")
        self.frontend_pid_label.grid(row=3, column=3, sticky=tk.W)
        
        # 控制按钮框架
        control_frame = ttk.LabelFrame(main_frame, text="服务控制", padding="10")
        control_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 按钮布局
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # 配置按钮框架为3列布局
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        
        # 后端控制按钮（第一列）
        backend_frame = ttk.LabelFrame(button_frame, text="后端服务控制", padding="5")
        backend_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.start_backend_btn = ttk.Button(backend_frame, text="🚀 启动", command=self.start_backend_service)
        self.start_backend_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.stop_backend_btn = ttk.Button(backend_frame, text="⏹️ 停止", command=self.stop_backend_service)
        self.stop_backend_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.restart_backend_btn = ttk.Button(backend_frame, text="🔄 重启", command=self.restart_backend_service)
        self.restart_backend_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 前端控制按钮（第二列）
        frontend_frame = ttk.LabelFrame(button_frame, text="前端服务控制", padding="5")
        frontend_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.start_frontend_btn = ttk.Button(frontend_frame, text="🚀 启动", command=self.start_frontend_service)
        self.start_frontend_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.stop_frontend_btn = ttk.Button(frontend_frame, text="⏹️ 停止", command=self.stop_frontend_service)
        self.stop_frontend_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.restart_frontend_btn = ttk.Button(frontend_frame, text="🔄 重启", command=self.restart_frontend_service)
        self.restart_frontend_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 通用操作按钮（第三列）
        common_frame = ttk.LabelFrame(button_frame, text="通用操作", padding="5")
        common_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.health_btn = ttk.Button(common_frame, text="🏥 检查", command=self.health_check)
        self.health_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.test_api_btn = ttk.Button(common_frame, text="🧪 测试", command=self.test_api)
        self.test_api_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.kill_port_btn = ttk.Button(common_frame, text="💀 清理端口", command=self.kill_port_processes)
        self.kill_port_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.open_web_btn = ttk.Button(common_frame, text="🌐 打开", command=self.open_frontend)
        self.open_web_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 日志框架
        log_frame = ttk.LabelFrame(main_frame, text="服务日志", padding="10")
        log_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(2, weight=1)
        
        # 日志标签切换
        log_tab_frame = ttk.Frame(log_frame)
        log_tab_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.system_tab_btn = ttk.Button(log_tab_frame, text="系统日志", 
                                        command=lambda: self.switch_log_tab("system"))
        self.system_tab_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.backend_tab_btn = ttk.Button(log_tab_frame, text="后端日志", 
                                         command=lambda: self.switch_log_tab("backend"))
        self.backend_tab_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.frontend_tab_btn = ttk.Button(log_tab_frame, text="前端日志", 
                                          command=lambda: self.switch_log_tab("frontend"))
        self.frontend_tab_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # 当前日志标签指示器
        self.current_tab_label = ttk.Label(log_tab_frame, text="[ 系统日志 ]", 
                                          font=('Microsoft YaHei', 9, 'bold'))
        self.current_tab_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 日志控制按钮
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(log_control_frame, text="📋 复制选中", 
                  command=self.copy_selected_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_control_frame, text="📄 复制全部", 
                  command=self.copy_all_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_control_frame, text="🔄 刷新日志", 
                  command=self.refresh_current_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_control_frame, text="🗑️ 清空当前日志", 
                  command=self.clear_current_logs).pack(side=tk.LEFT, padx=(0, 5))
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 初始化日志
        self.add_log("服务管理器已启动", "INFO")
    
    def add_log(self, message, level="INFO", source="system"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 根据消息来源分类存储
        if source == "backend" or "[后端-" in message:
            self.backend_logs.append(log_entry)
            source = "backend"
        elif source == "frontend" or "[前端-" in message:
            self.frontend_logs.append(log_entry)
            source = "frontend"
        else:
            self.system_logs.append(log_entry)
            source = "system"
        
        # 限制每个日志类型的条目数量
        if len(self.backend_logs) > 500:
            self.backend_logs = self.backend_logs[-500:]
        if len(self.frontend_logs) > 500:
            self.frontend_logs = self.frontend_logs[-500:]
        if len(self.system_logs) > 500:
            self.system_logs = self.system_logs[-500:]
        
        # 如果当前显示的是对应的日志类型，则立即更新显示
        if source == self.current_log_tab:
            self.log_queue.put(log_entry)
    
    def log_process_loop(self):
        """日志处理循环"""
        while True:
            try:
                log_entry = self.log_queue.get(timeout=0.1)
                self.root.after(0, self._update_log_display, log_entry)
            except queue.Empty:
                continue
    
    def _update_log_display(self, log_entry):
        """更新日志显示"""
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # 限制日志行数
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 200:
            self.log_text.delete("1.0", f"{len(lines) - 200}.0")
    
    def switch_log_tab(self, tab_name):
        """切换日志标签"""
        self.current_log_tab = tab_name
        
        # 更新标签指示器
        tab_labels = {
            "system": "[ 系统日志 ]",
            "backend": "[ 后端日志 ]", 
            "frontend": "[ 前端日志 ]"
        }
        self.current_tab_label.config(text=tab_labels.get(tab_name, "[ 未知 ]"))
        
        # 清空当前显示并重新加载对应日志
        self.log_text.delete("1.0", tk.END)
        
        # 获取对应的日志列表
        logs_to_show = []
        if tab_name == "system":
            logs_to_show = self.system_logs
        elif tab_name == "backend":
            logs_to_show = self.backend_logs
        elif tab_name == "frontend":
            logs_to_show = self.frontend_logs
        
        # 显示日志
        for log_entry in logs_to_show[-100:]:  # 只显示最近100条
            self.log_text.insert(tk.END, log_entry)
        
        self.log_text.see(tk.END)
    
    def status_update_loop(self):
        """状态更新循环"""
        while True:
            try:
                self.check_service_status()
                time.sleep(2)  # 每2秒检查一次
            except Exception as e:
                print(f"状态检查错误: {e}")
                time.sleep(5)
    
    def check_service_status(self):
        """检查服务状态"""
        self.check_backend_status()
        self.check_frontend_status()
    
    def check_backend_status(self):
        """检查后端服务状态"""
        # 先检查进程是否存在
        if self.backend_pid:
            try:
                process = psutil.Process(self.backend_pid)
                if not process.is_running():
                    # 进程已退出
                    self.backend_status = "stopped"
                    self.backend_pid = None
                    self.root.after(0, self._update_backend_status_display, "已停止", "gray")
                    return False
            except psutil.NoSuchProcess:
                # 进程不存在
                self.backend_status = "stopped"
                self.backend_pid = None
                self.root.after(0, self._update_backend_status_display, "已停止", "gray")
                return False
        
        # 检查健康状态
        try:
            response = requests.get(f"http://127.0.0.1:{self.backend_port}/healthz", 
                                  timeout=3)
            if response.status_code == 200:
                self.backend_status = "running"
                self.root.after(0, self._update_backend_status_display, "运行中", "green")
                return True
        except:
            pass
        
        # 如果有PID但健康检查失败，标记为异常
        if self.backend_pid:
            self.backend_status = "error"
            self.root.after(0, self._update_backend_status_display, "异常", "red")
            return False
        
        # 默认状态：已停止
        self.backend_status = "stopped"
        self.root.after(0, self._update_backend_status_display, "已停止", "gray")
        return False
    
    def check_frontend_status(self):
        """检查前端服务状态"""
        # 先检查进程是否存在
        if self.frontend_pid:
            try:
                process = psutil.Process(self.frontend_pid)
                if not process.is_running():
                    # 进程已退出
                    self.frontend_status = "stopped"
                    self.frontend_pid = None
                    self.root.after(0, self._update_frontend_status_display, "已停止", "gray")
                    return False
            except psutil.NoSuchProcess:
                # 进程不存在
                self.frontend_status = "stopped"
                self.frontend_pid = None
                self.root.after(0, self._update_frontend_status_display, "已停止", "gray")
                return False
        
        # 检查前端服务端口
        try:
            response = requests.get(f"http://127.0.0.1:{self.frontend_port}", 
                                  timeout=3)
            if response.status_code == 200:
                self.frontend_status = "running"
                self.root.after(0, self._update_frontend_status_display, "运行中", "green")
                return True
        except:
            pass
        
        # 如果有PID但端口检查失败，可能正在启动中
        if self.frontend_pid:
            self.frontend_status = "error"
            self.root.after(0, self._update_frontend_status_display, "启动中", "orange")
            return False
        
        # 默认状态：已停止
        self.frontend_status = "stopped"
        self.root.after(0, self._update_frontend_status_display, "已停止", "gray")
        return False
    
    def _update_backend_status_display(self, status_text, color):
        """更新后端状态显示"""
        self.backend_status_label.config(text=status_text, foreground=color)
        if self.backend_pid:
            self.backend_pid_label.config(text=str(self.backend_pid))
        else:
            self.backend_pid_label.config(text="--")
    
    def _update_frontend_status_display(self, status_text, color):
        """更新前端状态显示"""
        self.frontend_status_label.config(text=status_text, foreground=color)
        if self.frontend_pid:
            self.frontend_pid_label.config(text=str(self.frontend_pid))
        else:
            self.frontend_pid_label.config(text="--")
    
    def start_backend_service(self):
        """启动后端服务"""
        if self.backend_status == "running":
            self.add_log("后端服务已在运行中", "WARN")
            return
        
        self.add_log("正在启动后端服务...", "INFO")
        
        try:
            # 切换到后端目录
            backend_path = os.path.join(os.getcwd(), "backend")
            if not os.path.exists(backend_path):
                self.add_log(f"后端路径不存在: {backend_path}", "ERROR")
                return
            
            # 启动Python服务
            python_cmd = sys.executable
            self.backend_process = subprocess.Popen([
                python_cmd, "app/main.py", 
                "--port", str(self.backend_port),
                "--host", "127.0.0.1"
            ], cwd=backend_path, 
               stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE,
               text=True, bufsize=1, encoding='utf-8', errors='replace')
            
            self.backend_pid = self.backend_process.pid
            self.add_log(f"后端服务启动命令已发送，PID: {self.backend_pid}", "INFO")
            
            # 启动输出监控线程
            threading.Thread(target=self._monitor_backend_output, daemon=True).start()
            
        except Exception as e:
            self.add_log(f"启动后端服务失败: {e}", "ERROR")
    
    def start_frontend_service(self):
        """启动前端服务"""
        if self.frontend_status == "running":
            self.add_log("前端服务已在运行中", "WARN")
            return
        
        self.add_log("正在启动前端服务...", "INFO")
        
        try:
            # 切换到前端目录
            frontend_path = os.path.join(os.getcwd(), "frontend")
            if not os.path.exists(frontend_path):
                self.add_log(f"前端路径不存在: {frontend_path}", "ERROR")
                return
            
            # 启动前端开发服务器
            self.frontend_process = subprocess.Popen([
                "npm", "run", "dev"
            ], cwd=frontend_path, 
               stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE,
               text=True, bufsize=1,
               shell=True, encoding='utf-8', errors='replace')
            
            self.frontend_pid = self.frontend_process.pid
            self.add_log(f"前端服务启动命令已发送，PID: {self.frontend_pid}", "INFO")
            
            # 启动输出监控线程
            threading.Thread(target=self._monitor_frontend_output, daemon=True).start()
            
        except Exception as e:
            self.add_log(f"启动前端服务失败: {e}", "ERROR")
    
    def _monitor_backend_output(self):
        """监控后端服务输出"""
        if not self.backend_process:
            return
        
        # 监控stdout
        def monitor_stdout():
            for line in iter(self.backend_process.stdout.readline, ''):
                if line:
                    self.add_log(f"[后端-STDOUT] {line.strip()}", "INFO")
        
        # 监控stderr  
        def monitor_stderr():
            for line in iter(self.backend_process.stderr.readline, ''):
                if line:
                    line_content = line.strip()
                    # 根据日志级别分类
                    if "| INFO " in line_content:
                        self.add_log(f"{line_content}", "INFO", "backend")
                    elif "| ERROR " in line_content:
                        self.add_log(f"{line_content}", "ERROR", "backend")
                    elif "| WARNING " in line_content or "| WARN " in line_content:
                        self.add_log(f"{line_content}", "WARN", "backend")
                    else:
                        self.add_log(f"{line_content}", "ERROR", "backend")
        
        threading.Thread(target=monitor_stdout, daemon=True).start()
        threading.Thread(target=monitor_stderr, daemon=True).start()
    
    def _monitor_frontend_output(self):
        """监控前端服务输出"""
        if not self.frontend_process:
            return
        
        # 监控stdout
        def monitor_stdout():
            for line in iter(self.frontend_process.stdout.readline, ''):
                if line:
                    line_content = line.strip()
                    self.add_log(f"{line_content}", "INFO", "frontend")
                    
                    # 从Vite输出中提取端口号
                    if "Local:" in line_content and "localhost:" in line_content:
                        import re
                        port_match = re.search(r'localhost:(\d+)', line_content)
                        if port_match:
                            self.frontend_port = int(port_match.group(1))
                            self.add_log(f"检测到前端端口: {self.frontend_port}", "INFO", "system")
        
        # 监控stderr  
        def monitor_stderr():
            for line in iter(self.frontend_process.stderr.readline, ''):
                if line:
                    line_content = line.strip()
                    if "deprecated" in line_content.lower():
                        self.add_log(f"{line_content}", "WARN", "frontend")
                    else:
                        self.add_log(f"{line_content}", "ERROR", "frontend")
        
        threading.Thread(target=monitor_stdout, daemon=True).start()
        threading.Thread(target=monitor_stderr, daemon=True).start()
    
    def stop_backend_service(self):
        """停止后端服务"""
        if self.backend_status == "stopped":
            self.add_log("后端服务未运行", "WARN")
            return
        
        self.add_log("正在停止后端服务...", "INFO")
        
        try:
            if self.backend_process:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                self.add_log("后端服务已停止", "INFO")
            elif self.backend_pid:
                process = psutil.Process(self.backend_pid)
                process.terminate()
                process.wait(timeout=5)
                self.add_log("后端服务已停止", "INFO")
        except Exception as e:
            # 尝试强制终止
            try:
                if self.backend_pid:
                    import os
                    if os.name == 'nt':  # Windows
                        os.system(f'taskkill //PID {self.backend_pid} //F')
                    else:  # Unix/Linux
                        os.system(f'kill -9 {self.backend_pid}')
                self.add_log("后端服务已强制停止", "INFO")
            except:
                self.add_log(f"停止后端服务失败: {e}", "ERROR")
        finally:
            self.backend_process = None
            self.backend_pid = None
            self.backend_status = "stopped"
            # 立即更新状态显示
            self.root.after(0, self._update_backend_status_display, "已停止", "gray")
    
    def stop_frontend_service(self):
        """停止前端服务"""
        if self.frontend_status == "stopped":
            self.add_log("前端服务未运行", "WARN")
            return
        
        self.add_log("正在停止前端服务...", "INFO")
        
        try:
            if self.frontend_process:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
                self.add_log("前端服务已停止", "INFO")
            elif self.frontend_pid:
                process = psutil.Process(self.frontend_pid)
                process.terminate()
                process.wait(timeout=5)
                self.add_log("前端服务已停止", "INFO")
        except Exception as e:
            # 尝试强制终止
            try:
                if self.frontend_pid:
                    import os
                    if os.name == 'nt':  # Windows
                        os.system(f'taskkill //PID {self.frontend_pid} //F')
                    else:  # Unix/Linux
                        os.system(f'kill -9 {self.frontend_pid}')
                self.add_log("前端服务已强制停止", "INFO")
            except:
                self.add_log(f"停止前端服务失败: {e}", "ERROR")
        finally:
            self.frontend_process = None
            self.frontend_pid = None
            self.frontend_status = "stopped"
            # 立即更新状态显示
            self.root.after(0, self._update_frontend_status_display, "已停止", "gray")
    
    def restart_backend_service(self):
        """重启后端服务"""
        self.add_log("正在重启后端服务...", "INFO")
        self.stop_backend_service()
        time.sleep(2)
        self.start_backend_service()
    
    def restart_frontend_service(self):
        """重启前端服务"""
        self.add_log("正在重启前端服务...", "INFO")
        self.stop_frontend_service()
        time.sleep(2)
        self.start_frontend_service()
    
    def health_check(self):
        """健康检查"""
        self.add_log("执行健康检查...", "INFO")
        
        try:
            response = requests.get(f"http://127.0.0.1:{self.backend_port}/healthz", 
                                  timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.add_log(f"✅ 后端健康检查通过: {data}", "INFO")
            else:
                self.add_log(f"❌ 后端健康检查失败: HTTP {response.status_code}", "ERROR")
        except Exception as e:
            self.add_log(f"❌ 后端健康检查失败: {e}", "ERROR")
        
        # 检查前端服务
        try:
            response = requests.get(f"http://127.0.0.1:{self.frontend_port}", 
                                  timeout=5)
            if response.status_code == 200:
                self.add_log(f"✅ 前端健康检查通过", "INFO")
            else:
                self.add_log(f"❌ 前端健康检查失败: HTTP {response.status_code}", "ERROR")
        except Exception as e:
            self.add_log(f"❌ 前端健康检查失败: {e}", "ERROR")
    
    def test_api(self):
        """测试API接口"""
        self.add_log("开始API测试...", "INFO")
        
        # 测试各个API端点
        test_endpoints = [
            ("/healthz", "健康检查"),
            ("/api/v1/data/status", "数据状态"),
            ("/api/v1/data/labels", "数据标签"),
            ("/api/v1/strategies", "策略列表")
        ]
        
        for endpoint, name in test_endpoints:
            try:
                response = requests.get(f"http://127.0.0.1:{self.backend_port}{endpoint}", 
                                      timeout=3)
                if response.status_code == 200:
                    self.add_log(f"✅ {name}: 正常", "INFO")
                else:
                    self.add_log(f"❌ {name}: HTTP {response.status_code}", "ERROR")
            except Exception as e:
                self.add_log(f"❌ {name}: {e}", "ERROR")
    
    def kill_port_processes(self):
        """清理占用端口的进程"""
        self.add_log("开始清理端口进程...", "INFO")
        
        ports_to_check = [self.backend_port, self.frontend_port]
        
        for port in ports_to_check:
            try:
                # Windows命令查找占用端口的进程
                import subprocess
                result = subprocess.run(f'netstat -ano | findstr :{port}', 
                                      shell=True, capture_output=True, text=True)
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    pids = set()
                    
                    for line in lines:
                        if 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                if pid != '0':
                                    pids.add(pid)
                    
                    for pid in pids:
                        try:
                            subprocess.run(f'taskkill //PID {pid} //F', 
                                         shell=True, capture_output=True)
                            self.add_log(f"已终止占用端口{port}的进程PID:{pid}", "INFO")
                        except:
                            pass
                else:
                    self.add_log(f"端口{port}未被占用", "INFO")
                    
            except Exception as e:
                self.add_log(f"清理端口{port}失败: {e}", "ERROR")
        
        # 重置状态
        self.backend_pid = None
        self.frontend_pid = None
        self.backend_status = "stopped"
        self.frontend_status = "stopped"
        self.root.after(0, self._update_backend_status_display, "已停止", "gray")
        self.root.after(0, self._update_frontend_status_display, "已停止", "gray")
        
        self.add_log("端口清理完成", "INFO")
    
    def open_frontend(self):
        """打开前端界面"""
        import webbrowser
        url = f"http://localhost:{self.frontend_port}"  # 前端开发服务器端口
        webbrowser.open(url)
        self.add_log(f"已尝试打开前端界面: {url}", "INFO")
    
    def copy_selected_logs(self):
        """复制选中的日志"""
        try:
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.add_log("已复制选中日志到剪贴板", "INFO")
        except tk.TclError:
            self.add_log("没有选中的日志内容", "WARN")
    
    def copy_all_logs(self):
        """复制全部当前标签日志"""
        all_text = self.log_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(all_text)
        self.add_log(f"已复制{self.current_log_tab}日志到剪贴板", "INFO")
    
    def refresh_current_logs(self):
        """刷新当前标签日志显示"""
        self.add_log("正在刷新日志显示...", "INFO")
        # 重新切换到当前标签，这会重新加载日志
        self.switch_log_tab(self.current_log_tab)
    
    def clear_current_logs(self):
        """清空当前标签日志"""
        # 清空对应的日志存储
        if self.current_log_tab == "system":
            self.system_logs = []
        elif self.current_log_tab == "backend":
            self.backend_logs = []
        elif self.current_log_tab == "frontend":
            self.frontend_logs = []
        
        # 清空显示
        self.log_text.delete("1.0", tk.END)
        self.add_log(f"{self.current_log_tab}日志已清空", "INFO")
    
    def run(self):
        """运行GUI"""
        # 设置关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """关闭事件处理"""
        if messagebox.askokcancel("退出", "确定要退出服务管理器吗？"):
            # 停止所有服务
            if self.backend_status == "running":
                self.stop_backend_service()
            if self.frontend_status == "running":
                self.stop_frontend_service()
            self.root.destroy()


if __name__ == "__main__":
    app = ServiceManagerGUI()
    app.run()