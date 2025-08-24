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
        self.vite_pid = None  # Vite开发服务器PID
        self.electron_pid = None  # Electron应用PID
        
        # 配置诊断结果
        self.config_issues = []
        
        # 端口占用监控
        self.port_occupation_data = {}
        self.port_monitoring_enabled = True
        
        # 日志队列和存储
        self.log_queue = queue.Queue()
        self.backend_logs = []
        self.frontend_logs = []
        self.system_logs = []
        self.current_log_tab = "system"  # system, backend, frontend
        
        # 执行配置诊断
        self.diagnose_configuration()
        
        # 创建界面
        self.create_widgets()
        
        # 启动状态更新线程
        self.status_thread = threading.Thread(target=self.status_update_loop, daemon=True)
        self.status_thread.start()
        
        # 启动日志处理线程
        self.log_thread = threading.Thread(target=self.log_process_loop, daemon=True)
        self.log_thread.start()
        
        # 启动端口监控线程
        self.port_monitor_thread = threading.Thread(target=self.port_monitoring_loop, daemon=True)
        self.port_monitor_thread.start()
    
    def diagnose_configuration(self):
        """配置诊断功能 - 检查端口配置一致性"""
        self.config_issues = []
        
        try:
            # 检查前端vite.config.ts中的端口配置
            vite_config_path = os.path.join(os.getcwd(), "frontend", "vite.config.ts")
            if os.path.exists(vite_config_path):
                with open(vite_config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 查找port配置
                    import re
                    port_match = re.search(r'port:\s*(\d+)', content)
                    if port_match:
                        vite_port = int(port_match.group(1))
                        if vite_port != self.frontend_port:
                            self.config_issues.append({
                                'type': 'error',
                                'message': f'端口配置不一致！Python配置前端端口为{self.frontend_port}，但vite.config.ts中配置为{vite_port}'
                            })
                    
                    # 检查strictPort配置
                    if 'strictPort: true' not in content:
                        self.config_issues.append({
                            'type': 'warning', 
                            'message': 'vite.config.ts中缺少strictPort: true配置，可能导致端口漂移'
                        })
        except Exception as e:
            self.config_issues.append({
                'type': 'warning',
                'message': f'无法检查vite.config.ts: {str(e)}'
            })
        
        try:
            # 检查package.json中electron:dev的wait-on配置
            package_json_path = os.path.join(os.getcwd(), "frontend", "package.json")
            if os.path.exists(package_json_path):
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    electron_dev = data.get('scripts', {}).get('electron:dev', '')
                    if 'wait-on http://localhost:' in electron_dev:
                        # 提取wait-on的端口
                        import re
                        wait_on_match = re.search(r'wait-on http://localhost:(\d+)', electron_dev)
                        if wait_on_match:
                            wait_on_port = int(wait_on_match.group(1))
                            if wait_on_port != self.frontend_port:
                                self.config_issues.append({
                                    'type': 'error',
                                    'message': f'Electron等待端口不一致！期望{self.frontend_port}，但package.json中wait-on配置为{wait_on_port}'
                                })
        except Exception as e:
            self.config_issues.append({
                'type': 'warning',
                'message': f'无法检查package.json: {str(e)}'
            })
        
        # 检查端口可用性
        if not self.is_port_available(self.backend_port):
            self.config_issues.append({
                'type': 'warning',
                'message': f'后端端口{self.backend_port}已被占用'
            })
            
        if not self.is_port_available(self.frontend_port):
            self.config_issues.append({
                'type': 'warning', 
                'message': f'前端端口{self.frontend_port}已被占用'
            })
    
    def is_port_available(self, port):
        """检查端口是否可用"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result != 0
        except:
            return False
    
    def scan_port_occupation(self):
        """扫描端口占用情况"""
        import subprocess
        import re
        
        port_data = {}
        important_ports = [self.backend_port, self.frontend_port, 5173, 5174, 5175, 5176, 5177, 5178, 5179, 5180]
        
        try:
            # Windows 命令获取端口占用信息
            result = subprocess.run('netstat -ano', shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            try:
                                address = parts[1]
                                pid = parts[4]
                                
                                # 提取端口号
                                if ':' in address:
                                    port_str = address.split(':')[-1]
                                    if port_str.isdigit():
                                        port = int(port_str)
                                        
                                        # 只关注重要端口
                                        if port in important_ports:
                                            # 获取进程信息
                                            process_name = self.get_process_name(pid)
                                            port_data[port] = {
                                                'pid': pid,
                                                'process_name': process_name,
                                                'address': address,
                                                'is_system_service': port in [self.backend_port, self.frontend_port]
                                            }
                            except (ValueError, IndexError):
                                continue
        except Exception as e:
            self.add_log(f"端口扫描失败: {e}", "ERROR")
        
        return port_data
    
    def get_process_name(self, pid):
        """根据PID获取进程名"""
        try:
            process = psutil.Process(int(pid))
            return process.name()
        except (psutil.NoSuchProcess, ValueError):
            return "未知进程"
    
    def port_monitoring_loop(self):
        """端口监控循环"""
        while True:
            try:
                if self.port_monitoring_enabled:
                    new_data = self.scan_port_occupation()
                    if new_data != self.port_occupation_data:
                        self.port_occupation_data = new_data
                        self.root.after(0, self._update_port_display)
                time.sleep(5)  # 每5秒检查一次
            except Exception as e:
                print(f"端口监控错误: {e}")
                time.sleep(10)
    
    def _update_port_display(self):
        """更新端口显示"""
        if hasattr(self, 'port_text'):
            self.port_text.config(state=tk.NORMAL)
            self.port_text.delete("1.0", tk.END)
            
            # 显示重要端口状态
            important_ports = [self.backend_port, self.frontend_port, 5173, 5174, 5175, 5176]
            
            for port in sorted(important_ports):
                if port in self.port_occupation_data:
                    data = self.port_occupation_data[port]
                    pid = data['pid']
                    process_name = data['process_name']
                    
                    # 检查是否是我们的系统服务
                    is_our_service = (
                        (port == self.backend_port and pid == str(self.backend_pid)) or
                        (port == self.frontend_port and pid == str(self.vite_pid))
                    )
                    
                    if is_our_service:
                        status_line = f"端口 {port}: ✅ {process_name} (PID: {pid}) [系统服务]\n"
                        self.port_text.insert(tk.END, status_line, "system")
                    else:
                        status_line = f"端口 {port}: ⚠️ {process_name} (PID: {pid}) [外部进程]\n"
                        self.port_text.insert(tk.END, status_line, "occupied")
                else:
                    status_line = f"端口 {port}: 🔓 可用\n"
                    self.port_text.insert(tk.END, status_line, "available")
            
            # 添加统计信息
            occupied_count = len([p for p in important_ports if p in self.port_occupation_data])
            available_count = len(important_ports) - occupied_count
            
            self.port_text.insert(tk.END, f"\n📊 统计: {occupied_count}个已占用, {available_count}个可用\n", "info")
            
            # 添加更新时间
            from datetime import datetime
            update_time = datetime.now().strftime("%H:%M:%S")
            self.port_text.insert(tk.END, f"🕐 更新时间: {update_time}\n", "info")
            
            self.port_text.config(state=tk.DISABLED)
    
    def kill_specific_process(self, pid):
        """终止指定进程"""
        try:
            import os
            if os.name == 'nt':  # Windows
                result = subprocess.run(f'taskkill /PID {pid} /F', 
                                      shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.add_log(f"已终止进程 PID: {pid}", "INFO")
                    return True
                else:
                    self.add_log(f"终止进程失败 PID: {pid} - {result.stderr}", "ERROR")
                    return False
            else:  # Unix/Linux
                os.system(f'kill -9 {pid}')
                self.add_log(f"已终止进程 PID: {pid}", "INFO")
                return True
        except Exception as e:
            self.add_log(f"终止进程失败: {e}", "ERROR")
            return False
    
    def manual_port_refresh(self):
        """手动刷新端口监控"""
        self.add_log("手动刷新端口监控...", "INFO")
        try:
            new_data = self.scan_port_occupation()
            self.port_occupation_data = new_data
            self._update_port_display()
            self.add_log("端口监控刷新完成", "INFO")
        except Exception as e:
            self.add_log(f"端口监控刷新失败: {e}", "ERROR")
    
    def clean_conflicting_ports(self):
        """清理冲突端口进程"""
        self.add_log("开始清理冲突端口进程...", "INFO")
        
        system_ports = [self.backend_port, self.frontend_port]
        conflicting_processes = []
        
        # 找出占用系统端口的非系统进程
        for port, data in self.port_occupation_data.items():
            if port in system_ports:
                pid = data['pid']
                process_name = data['process_name']
                
                # 检查是否是我们自己的服务进程
                is_our_process = (
                    (port == self.backend_port and pid == str(self.backend_pid)) or
                    (port == self.frontend_port and pid == str(self.vite_pid))
                )
                
                if not is_our_process:
                    conflicting_processes.append((port, pid, process_name))
        
        if not conflicting_processes:
            self.add_log("未发现端口冲突", "INFO")
            return
        
        # 清理冲突进程
        for port, pid, process_name in conflicting_processes:
            self.add_log(f"清理端口{port}上的冲突进程: {process_name} (PID: {pid})", "WARN")
            if self.kill_specific_process(pid):
                self.add_log(f"✅ 成功清理端口{port}的冲突进程", "INFO")
            else:
                self.add_log(f"❌ 清理端口{port}的进程失败", "ERROR")
        
        # 等待一下然后刷新监控
        import time
        time.sleep(2)
        self.manual_port_refresh()
    
    def create_config_diagnosis_frame(self, parent, row):
        """创建配置诊断框架"""
        diag_frame = ttk.LabelFrame(parent, text="⚠️ 配置诊断", padding="10")
        diag_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建滚动文本框显示诊断结果
        diag_text = tk.Text(diag_frame, height=4, wrap=tk.WORD, font=('Consolas', 9))
        diag_text.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # 滚动条
        diag_scrollbar = ttk.Scrollbar(diag_frame, orient=tk.VERTICAL, command=diag_text.yview)
        diag_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        diag_text.config(yscrollcommand=diag_scrollbar.set)
        
        # 配置文本标签颜色
        diag_text.tag_configure("error", foreground="red", font=('Consolas', 9, 'bold'))
        diag_text.tag_configure("warning", foreground="orange", font=('Consolas', 9))
        diag_text.tag_configure("info", foreground="blue", font=('Consolas', 9))
        
        # 插入诊断结果
        for issue in self.config_issues:
            issue_text = f"[{issue['type'].upper()}] {issue['message']}\n"
            diag_text.insert(tk.END, issue_text, issue['type'])
        
        # 添加重新诊断按钮
        recheck_btn = ttk.Button(diag_frame, text="🔄 重新检查配置", 
                                command=self.recheck_configuration)
        recheck_btn.grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
        diag_frame.columnconfigure(0, weight=1)
        
        # 设置只读
        diag_text.config(state=tk.DISABLED)
    
    def recheck_configuration(self):
        """重新检查配置"""
        self.diagnose_configuration()
        # 重新创建界面
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_widgets()
        self.add_log("配置重新检查完成", "INFO")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🎛️ 量化回测系统 - 统一控制中心", 
                               font=('Microsoft YaHei', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 配置诊断框架 - 如果有问题才显示
        if self.config_issues:
            self.create_config_diagnosis_frame(main_frame, row=1)
            status_row = 2
        else:
            status_row = 1
        
        # 服务状态框架 - 显化端口信息
        status_frame = ttk.LabelFrame(main_frame, text="📊 服务状态监控", padding="10")
        status_frame.grid(row=status_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(3, weight=1)
        
        # 后端服务状态 - 端口信息突出显示
        backend_title = f"后端API服务 [端口: {self.backend_port}]"
        ttk.Label(status_frame, text=backend_title, font=('Microsoft YaHei', 10, 'bold'), 
                 foreground='blue').grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(status_frame, text="状态:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_status_label = ttk.Label(status_frame, text="检查中...", foreground="orange")
        self.backend_status_label.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="进程PID:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_pid_label = ttk.Label(status_frame, text="--")
        self.backend_pid_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="健康检查:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_health_label = ttk.Label(status_frame, text="未检查", foreground="gray")
        self.backend_health_label.grid(row=3, column=1, sticky=tk.W)
        
        # 前端服务状态 - 端口信息突出显示
        frontend_title = f"前端开发服务 [端口: {self.frontend_port}]"
        ttk.Label(status_frame, text=frontend_title, font=('Microsoft YaHei', 10, 'bold'), 
                 foreground='green').grid(row=0, column=2, columnspan=2, sticky=tk.W, padx=(20, 10))
        
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
        
        # 配置按钮框架为4列布局
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1) 
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)
        
        # 后端控制按钮（第一列）
        backend_frame = ttk.LabelFrame(button_frame, text="后端API服务", padding="5")
        backend_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 3))
        
        self.start_backend_btn = ttk.Button(backend_frame, text="🚀 启动", command=self.start_backend_service)
        self.start_backend_btn.pack(fill=tk.BOTH, expand=True, pady=(0, 1))
        
        self.stop_backend_btn = ttk.Button(backend_frame, text="⏹️ 停止", command=self.stop_backend_service)
        self.stop_backend_btn.pack(fill=tk.BOTH, expand=True, pady=(0, 1))
        
        self.restart_backend_btn = ttk.Button(backend_frame, text="🔄 重启", command=self.restart_backend_service)
        self.restart_backend_btn.pack(fill=tk.BOTH, expand=True)
        
        # Vite开发服务器控制（第二列）
        vite_frame = ttk.LabelFrame(button_frame, text="🎯 步骤1: Vite开发服务", padding="5")
        vite_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 3))
        
        self.start_vite_btn = ttk.Button(vite_frame, text="🚀 启动Vite服务", command=self.start_vite_service)
        self.start_vite_btn.pack(fill=tk.BOTH, expand=True, pady=(0, 1))
        
        self.stop_vite_btn = ttk.Button(vite_frame, text="⏹️ 停止Vite", command=self.stop_vite_service)
        self.stop_vite_btn.pack(fill=tk.BOTH, expand=True, pady=(0, 1))
        
        # Vite状态标签
        self.vite_status_label = ttk.Label(vite_frame, text="未启动", foreground="gray", font=('Microsoft YaHei', 8))
        self.vite_status_label.pack(fill=tk.BOTH, expand=True)
        
        # Electron桌面应用控制（第三列）
        electron_frame = ttk.LabelFrame(button_frame, text="🎯 步骤2: Electron应用", padding="5")
        electron_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 3))
        
        self.start_electron_btn = ttk.Button(electron_frame, text="🖥️ 打开桌面应用", 
                                           command=self.start_electron_app, state=tk.DISABLED)
        self.start_electron_btn.pack(fill=tk.BOTH, expand=True, pady=(0, 1))
        
        self.stop_electron_btn = ttk.Button(electron_frame, text="❌ 关闭应用", 
                                          command=self.stop_electron_app, state=tk.DISABLED)
        self.stop_electron_btn.pack(fill=tk.BOTH, expand=True, pady=(0, 1))
        
        # Electron状态标签 
        self.electron_status_label = ttk.Label(electron_frame, text="等待Vite就绪", foreground="gray", font=('Microsoft YaHei', 8))
        self.electron_status_label.pack(fill=tk.BOTH, expand=True)
        
        # 通用操作按钮（第四列）
        common_frame = ttk.LabelFrame(button_frame, text="系统操作", padding="5")
        common_frame.grid(row=0, column=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.health_btn = ttk.Button(common_frame, text="🏥 检查", command=self.health_check)
        self.health_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.test_api_btn = ttk.Button(common_frame, text="🧪 测试", command=self.test_api)
        self.test_api_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.kill_port_btn = ttk.Button(common_frame, text="💀 清理端口", command=self.kill_port_processes)
        self.kill_port_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.open_web_btn = ttk.Button(common_frame, text="🌐 打开", command=self.open_frontend)
        self.open_web_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 端口监控框架
        port_frame = ttk.LabelFrame(main_frame, text="📡 实时端口监控", padding="10")
        port_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        port_frame.columnconfigure(0, weight=1)
        
        # 端口监控标题和控制
        port_control_frame = ttk.Frame(port_frame)
        port_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(port_control_frame, text="重要端口占用状态:", 
                 font=('Microsoft YaHei', 9, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(port_control_frame, text="🔄 刷新", 
                  command=self.manual_port_refresh).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(port_control_frame, text="🧹 清理冲突", 
                  command=self.clean_conflicting_ports).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 端口状态显示区域
        self.port_text = tk.Text(port_frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
        self.port_text.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # 端口显示滚动条
        port_scrollbar = ttk.Scrollbar(port_frame, orient=tk.VERTICAL, command=self.port_text.yview)
        port_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.port_text.config(yscrollcommand=port_scrollbar.set)
        
        # 配置端口文本颜色标签
        self.port_text.tag_configure("occupied", foreground="red", font=('Consolas', 9, 'bold'))
        self.port_text.tag_configure("available", foreground="green", font=('Consolas', 9))
        self.port_text.tag_configure("system", foreground="blue", font=('Consolas', 9, 'bold'))
        self.port_text.tag_configure("info", foreground="gray", font=('Consolas', 8))
        
        # 设置只读
        self.port_text.config(state=tk.DISABLED)
        
        # 日志框架
        log_frame = ttk.LabelFrame(main_frame, text="服务日志", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
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
        
        # 日志控制按钮 - 分两行显示
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 第一行控制按钮
        control_row1 = ttk.Frame(log_control_frame)
        control_row1.pack(fill=tk.X, pady=(0, 2))
        
        ttk.Button(control_row1, text="📋 复制选中", 
                  command=self.copy_selected_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="📄 复制全部", 
                  command=self.copy_all_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="🔄 刷新日志", 
                  command=self.refresh_current_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_row1, text="🗑️ 清空当前日志", 
                  command=self.clear_current_logs).pack(side=tk.LEFT, padx=(0, 5))
        
        # 第二行增强功能
        control_row2 = ttk.Frame(log_control_frame)
        control_row2.pack(fill=tk.X)
        
        # 日志级别过滤
        ttk.Label(control_row2, text="级别:").pack(side=tk.LEFT, padx=(0, 2))
        self.log_level_var = tk.StringVar(value="ALL")
        log_level_combo = ttk.Combobox(control_row2, textvariable=self.log_level_var, 
                                     values=["ALL", "INFO", "WARN", "ERROR"], width=8)
        log_level_combo.pack(side=tk.LEFT, padx=(0, 5))
        log_level_combo.bind('<<ComboboxSelected>>', self.on_log_level_change)
        
        # 自动滚动开关
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(control_row2, text="自动滚动", 
                                          variable=self.auto_scroll_var)
        auto_scroll_check.pack(side=tk.LEFT, padx=(0, 5))
        
        # 搜索功能
        ttk.Label(control_row2, text="搜索:").pack(side=tk.LEFT, padx=(5, 2))
        self.log_search_var = tk.StringVar()
        self.log_search_entry = ttk.Entry(control_row2, textvariable=self.log_search_var, width=12)
        self.log_search_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.log_search_entry.bind('<KeyRelease>', self.on_log_search)
        ttk.Button(control_row2, text="🔍", command=self.highlight_search_results, width=3).pack(side=tk.LEFT, padx=(0, 5))
        
        # 日志统计显示
        self.log_stats_label = ttk.Label(control_row2, text="", font=('Microsoft YaHei', 8), 
                                       foreground="gray")
        self.log_stats_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, 
                                                font=('Consolas', 9))
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置日志文本标签 - 增强格式化
        self.log_text.tag_configure("INFO", foreground="#2e7d32", font=('Consolas', 9))
        self.log_text.tag_configure("WARN", foreground="#f57c00", font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure("ERROR", foreground="#d32f2f", font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure("timestamp", foreground="#666666", font=('Consolas', 8))
        self.log_text.tag_configure("highlight", background="#ffeb3b", font=('Consolas', 9, 'bold'))
        
        # 初始化日志
        self.add_log("服务管理器已启动", "INFO")
        self._update_log_stats()
    
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
        # 检查是否符合级别过滤
        level_filter = getattr(self, 'log_level_var', None)
        if level_filter and level_filter.get() != "ALL":
            if f"] [{level_filter.get()}]" not in log_entry:
                return
        
        # 使用格式化插入
        self._insert_formatted_log(log_entry)
        
        # 自动滚动
        if getattr(self, 'auto_scroll_var', None) and self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        # 更新统计
        self._update_log_stats()
        
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
        
        # 使用增强的过滤刷新
        self._refresh_filtered_logs()
        self._update_log_stats()
    
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
    
    def start_vite_service(self):
        """步骤1：启动Vite开发服务器"""
        if self.vite_pid and self.is_process_running(self.vite_pid):
            self.add_log("Vite开发服务器已在运行中", "WARN")
            return
        
        self.add_log("🎯 步骤1：正在启动Vite开发服务器...", "INFO")
        
        try:
            # 切换到前端目录
            frontend_path = os.path.join(os.getcwd(), "frontend")
            if not os.path.exists(frontend_path):
                self.add_log(f"前端路径不存在: {frontend_path}", "ERROR")
                return
            
            # 启动Vite开发服务器
            self.vite_process = subprocess.Popen([
                "npm", "run", "dev"
            ], cwd=frontend_path, 
               stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE,
               text=True, bufsize=1,
               shell=True, encoding='utf-8', errors='replace')
            
            self.vite_pid = self.vite_process.pid
            self.add_log(f"Vite开发服务器启动中，PID: {self.vite_pid}", "INFO")
            self.vite_status_label.config(text="启动中...", foreground="orange")
            
            # 启动Vite输出监控线程
            threading.Thread(target=self._monitor_vite_output, daemon=True).start()
            
            # 启动Vite状态检查线程
            threading.Thread(target=self._check_vite_ready, daemon=True).start()
            
        except Exception as e:
            self.add_log(f"启动Vite服务器失败: {e}", "ERROR")
            self.vite_status_label.config(text="启动失败", foreground="red")
    
    def stop_vite_service(self):
        """停止Vite开发服务器"""
        if not self.vite_pid:
            self.add_log("Vite服务器未运行", "WARN")
            return
        
        self.add_log("正在停止Vite开发服务器...", "INFO")
        
        try:
            if hasattr(self, 'vite_process') and self.vite_process:
                self.vite_process.terminate()
                self.vite_process.wait(timeout=5)
            else:
                # 通过PID终止进程
                import os
                if os.name == 'nt':  # Windows
                    os.system(f'taskkill //PID {self.vite_pid} //F')
                else:  # Unix/Linux
                    os.system(f'kill -9 {self.vite_pid}')
            
            self.add_log("Vite服务器已停止", "INFO")
            
        except Exception as e:
            self.add_log(f"停止Vite服务器失败: {e}", "ERROR")
        finally:
            self.vite_pid = None
            self.vite_process = None
            self.vite_status_label.config(text="已停止", foreground="gray")
            # 禁用Electron按钮
            self.start_electron_btn.config(state=tk.DISABLED)
            self.electron_status_label.config(text="等待Vite就绪", foreground="gray")
    
    def start_electron_app(self):
        """步骤2：启动Electron桌面应用"""
        if self.electron_pid and self.is_process_running(self.electron_pid):
            self.add_log("Electron应用已在运行中", "WARN")
            return
        
        self.add_log("🖥️ 步骤2：正在启动Electron桌面应用...", "INFO")
        
        try:
            frontend_path = os.path.join(os.getcwd(), "frontend")
            
            # 启动Electron应用
            self.electron_process = subprocess.Popen([
                "npx", "electron", "electron/main.js"
            ], cwd=frontend_path,
               stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE,
               text=True, bufsize=1,
               shell=True, encoding='utf-8', errors='replace')
            
            self.electron_pid = self.electron_process.pid
            self.add_log(f"Electron桌面应用已启动，PID: {self.electron_pid}", "INFO")
            self.electron_status_label.config(text="运行中", foreground="green")
            
            # 监控Electron输出
            threading.Thread(target=self._monitor_electron_output, daemon=True).start()
            
        except Exception as e:
            self.add_log(f"启动Electron应用失败: {e}", "ERROR")
            self.electron_status_label.config(text="启动失败", foreground="red")
    
    def stop_electron_app(self):
        """停止Electron桌面应用"""
        if not self.electron_pid:
            self.add_log("Electron应用未运行", "WARN")
            return
        
        self.add_log("正在关闭Electron桌面应用...", "INFO")
        
        try:
            if hasattr(self, 'electron_process') and self.electron_process:
                self.electron_process.terminate()
                self.electron_process.wait(timeout=5)
            else:
                import os
                if os.name == 'nt':  # Windows
                    os.system(f'taskkill //PID {self.electron_pid} //F')
                else:  # Unix/Linux
                    os.system(f'kill -9 {self.electron_pid}')
            
            self.add_log("Electron应用已关闭", "INFO")
            
        except Exception as e:
            self.add_log(f"关闭Electron应用失败: {e}", "ERROR")
        finally:
            self.electron_pid = None
            self.electron_process = None
            self.electron_status_label.config(text="已关闭", foreground="gray")
    
    def is_process_running(self, pid):
        """检查进程是否在运行"""
        if not pid:
            return False
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
    
    def _check_vite_ready(self):
        """检查Vite服务是否就绪"""
        import time
        # 先等待3秒，给Vite足够时间完全启动并绑定端口
        time.sleep(3)
        
        max_attempts = 30  # 最多等待30秒
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(f"http://127.0.0.1:{self.frontend_port}", timeout=2)
                if response.status_code == 200:
                    # Vite就绪，启用Electron按钮
                    self.root.after(0, self._vite_ready_callback)
                    return
            except:
                pass
            
            time.sleep(1)
            attempt += 1
        
        # 超时，Vite启动失败
        self.root.after(0, self._vite_failed_callback)
    
    def _vite_ready_callback(self):
        """Vite就绪回调"""
        self.vite_status_label.config(text=f"运行中 :{self.frontend_port}", foreground="green")
        self.start_electron_btn.config(state=tk.NORMAL)
        self.stop_electron_btn.config(state=tk.NORMAL)
        self.electron_status_label.config(text="✅ 可以启动", foreground="blue")
        self.add_log(f"✅ Vite开发服务器就绪！运行在 http://localhost:{self.frontend_port}", "INFO")
    
    def _vite_failed_callback(self):
        """Vite启动失败回调"""
        self.vite_status_label.config(text="启动超时", foreground="red")
        self.add_log("❌ Vite开发服务器启动超时，请检查端口占用情况", "ERROR")
    
    def _monitor_vite_output(self):
        """监控Vite服务器输出"""
        if not hasattr(self, 'vite_process') or not self.vite_process:
            return
        
        def monitor_stdout():
            for line in iter(self.vite_process.stdout.readline, ''):
                if line:
                    line_content = line.strip()
                    self.add_log(f"[Vite] {line_content}", "INFO", "frontend")
        
        def monitor_stderr():
            for line in iter(self.vite_process.stderr.readline, ''):
                if line:
                    line_content = line.strip()
                    if "deprecated" in line_content.lower():
                        self.add_log(f"[Vite-WARN] {line_content}", "WARN", "frontend")
                    else:
                        self.add_log(f"[Vite-ERR] {line_content}", "ERROR", "frontend")
        
        threading.Thread(target=monitor_stdout, daemon=True).start()
        threading.Thread(target=monitor_stderr, daemon=True).start()
    
    def _monitor_electron_output(self):
        """监控Electron应用输出"""
        if not hasattr(self, 'electron_process') or not self.electron_process:
            return
        
        def monitor_stdout():
            for line in iter(self.electron_process.stdout.readline, ''):
                if line:
                    line_content = line.strip()
                    self.add_log(f"[Electron] {line_content}", "INFO", "frontend")
        
        def monitor_stderr():
            for line in iter(self.electron_process.stderr.readline, ''):
                if line:
                    line_content = line.strip()
                    self.add_log(f"[Electron-ERR] {line_content}", "ERROR", "frontend")
        
        threading.Thread(target=monitor_stdout, daemon=True).start()
        threading.Thread(target=monitor_stderr, daemon=True).start()
    
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
    
    def on_log_level_change(self, event=None):
        """日志级别过滤改变"""
        self._refresh_filtered_logs()
        self._update_log_stats()
    
    def on_log_search(self, event=None):
        """实时搜索日志"""
        # 延迟搜索，避免频繁更新
        if hasattr(self, '_search_timer'):
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(300, self.highlight_search_results)
    
    def highlight_search_results(self):
        """高亮搜索结果"""
        search_text = self.log_search_var.get().strip()
        
        # 清除之前的高亮
        self.log_text.tag_remove("highlight", "1.0", tk.END)
        
        if search_text:
            # 搜索并高亮所有匹配项
            start_pos = "1.0"
            while True:
                pos = self.log_text.search(search_text, start_pos, tk.END, nocase=True)
                if not pos:
                    break
                end_pos = f"{pos}+{len(search_text)}c"
                self.log_text.tag_add("highlight", pos, end_pos)
                start_pos = end_pos
    
    def _refresh_filtered_logs(self):
        """根据级别过滤刷新日志显示"""
        level_filter = self.log_level_var.get()
        
        # 获取当前标签的日志
        current_logs = []
        if self.current_log_tab == "system":
            current_logs = self.system_logs
        elif self.current_log_tab == "backend":
            current_logs = self.backend_logs
        elif self.current_log_tab == "frontend":
            current_logs = self.frontend_logs
        
        # 清空显示
        self.log_text.delete("1.0", tk.END)
        
        # 过滤并显示日志
        for log_entry in current_logs[-200:]:  # 只显示最近200条
            if level_filter == "ALL" or f"] [{level_filter}]" in log_entry:
                self._insert_formatted_log(log_entry)
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
    
    def _insert_formatted_log(self, log_entry):
        """插入格式化的日志条目"""
        # 解析日志条目的各部分
        import re
        
        # 匹配时间戳、级别和消息
        pattern = r'^\[(.*?)\] \[(.*?)\] (.*)$'
        match = re.match(pattern, log_entry.strip())
        
        if match:
            timestamp, level, message = match.groups()
            
            # 插入时间戳
            self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            
            # 插入级别标签
            self.log_text.insert(tk.END, f"[{level}] ", level)
            
            # 插入消息
            self.log_text.insert(tk.END, f"{message}\n")
        else:
            # 如果解析失败，直接插入原始日志
            self.log_text.insert(tk.END, log_entry)
    
    def _update_log_stats(self):
        """更新日志统计"""
        # 统计当前标签的日志数量
        current_logs = []
        if self.current_log_tab == "system":
            current_logs = self.system_logs
        elif self.current_log_tab == "backend":
            current_logs = self.backend_logs
        elif self.current_log_tab == "frontend":
            current_logs = self.frontend_logs
        
        # 按级别统计
        stats = {"INFO": 0, "WARN": 0, "ERROR": 0}
        for log in current_logs:
            for level in stats.keys():
                if f"] [{level}]" in log:
                    stats[level] += 1
                    break
        
        # 更新统计显示
        total = sum(stats.values())
        stats_text = f"总计: {total} | INFO: {stats['INFO']} | WARN: {stats['WARN']} | ERROR: {stats['ERROR']}"
        
        if hasattr(self, 'log_stats_label'):
            self.log_stats_label.config(text=stats_text)
    
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