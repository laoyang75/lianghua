#!/usr/bin/env python3
"""
简单测试脚本验证GUI组件
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# 测试基本imports
try:
    from ports_config import get_backend_port, get_frontend_port
    print("[OK] 端口配置导入成功")
    print(f"后端端口: {get_backend_port()}")
    print(f"前端端口: {get_frontend_port()}")
except ImportError as e:
    print(f"[ERROR] 端口配置导入失败: {e}")
    # 使用默认值
    def get_backend_port(): return 5318
    def get_frontend_port(): return 5187

# 创建简单测试窗口
def create_test_window():
    root = tk.Tk()
    root.title("服务管理器GUI - 测试")
    root.geometry("600x400")
    
    # 测试标签
    ttk.Label(root, text="量化回测系统 - 统一控制中心", 
             font=('Microsoft YaHei', 14, 'bold')).pack(pady=20)
    
    # 测试按钮
    ttk.Button(root, text="GUI测试成功", 
              command=lambda: print("按钮点击成功")).pack(pady=10)
    
    # 端口信息
    info_text = f"后端端口: {get_backend_port()}\n前端端口: {get_frontend_port()}"
    ttk.Label(root, text=info_text).pack(pady=10)
    
    return root

if __name__ == "__main__":
    print("启动GUI测试...")
    try:
        root = create_test_window()
        print("测试窗口创建成功")
        root.mainloop()
    except Exception as e:
        print(f"GUI测试失败: {e}")
        import traceback
        traceback.print_exc()