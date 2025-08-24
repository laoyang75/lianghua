#!/usr/bin/env python3
"""
简化的服务启动脚本
用于测试修复后的系统
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# 导入统一端口配置
try:
    from ports_config import get_backend_port, get_backend_url, get_frontend_port
    BACKEND_PORT = get_backend_port()
    BACKEND_URL = get_backend_url()
    FRONTEND_PORT = get_frontend_port()
except ImportError:
    BACKEND_PORT = 5318
    BACKEND_URL = "http://127.0.0.1:5318"
    FRONTEND_PORT = 5187

def start_backend():
    """启动后端服务"""
    print("🚀 启动后端服务...")
    
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    try:
        # 启动FastAPI服务
        cmd = [
            sys.executable, 
            "app/main.py", 
            "--port", str(BACKEND_PORT),
            "--host", "127.0.0.1"
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        print(f"✅ 后端服务已启动 (PID: {process.pid})")
        print(f"📍 服务地址: {BACKEND_URL}")
        print(f"📍 API文档: {BACKEND_URL}/docs")
        
        return process
        
    except Exception as e:
        print(f"❌ 启动后端服务失败: {e}")
        return None

def check_service():
    """检查服务状态"""
    import requests
    
    print("🔍 检查服务状态...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/healthz", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 后端服务健康: {data.get('status', 'unknown')}")
            print(f"📊 服务信息: {data.get('service', 'N/A')}")
            return True
        else:
            print(f"❌ 服务响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接服务: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("量化回测系统 - 服务启动器")
    print("=" * 50)
    
    # 启动后端
    backend_process = start_backend()
    
    if backend_process:
        print("\n⏳ 等待服务启动...")
        time.sleep(5)  # 等待服务启动
        
        # 检查服务
        if check_service():
            print("\n🎉 系统启动成功！")
            print("\n📋 可用端点:")
            print(f"- 健康检查: {BACKEND_URL}/healthz")
            print(f"- API文档: {BACKEND_URL}/docs")
            print(f"- 数据状态: {BACKEND_URL}/data/status")
            print(f"- 前端界面: http://localhost:{FRONTEND_PORT}")
        else:
            print("\n⚠️ 服务启动可能有问题，请检查日志")
    else:
        print("\n❌ 服务启动失败")

if __name__ == "__main__":
    main()