"""
测试后端服务启动
"""
import sys
import os
from pathlib import Path

# 添加backend路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from app.main import create_app
    import uvicorn
    
    print("创建FastAPI应用...")
    app = create_app()
    
    print("可用路由:")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  {route.path}")
            if hasattr(route, 'route_class'):
                print(f"    Methods: {getattr(route, 'methods', 'N/A')}")
    
    print("\n启动服务在端口5320...")
    uvicorn.run(app, host="127.0.0.1", port=5320, log_level="info")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()