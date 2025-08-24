#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化回测系统 - 统一端口配置
所有端口配置集中管理，避免硬编码
"""

import os
import json
from pathlib import Path
from typing import Dict, Any


class PortsConfig:
    """统一端口配置管理"""
    
    def __init__(self):
        self.config_file = Path(__file__).parent / "ports_config.json"
        self._config = self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "backend": {
                "port": 5318,
                "host": "127.0.0.1",
                "description": "后端API服务端口"
            },
            "frontend": {
                "port": 5187,  # Vite默认5173，但可能冲突，使用5187
                "host": "127.0.0.1", 
                "description": "前端开发服务器端口"
            },
            "websocket": {
                "port": 5319,
                "host": "127.0.0.1",
                "description": "WebSocket服务端口"
            },
            "port_pool": {
                "start": 5320,
                "end": 5350,
                "description": "动态端口分配池"
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 确保所有必需的键都存在
                default_config = self._get_default_config()
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"加载端口配置失败: {e}，使用默认配置")
        
        return self._get_default_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            print(f"端口配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"保存端口配置失败: {e}")
    
    def get_backend_port(self) -> int:
        """获取后端端口"""
        return self._config["backend"]["port"]
    
    def get_frontend_port(self) -> int:
        """获取前端端口"""
        return self._config["frontend"]["port"]
    
    def get_websocket_port(self) -> int:
        """获取WebSocket端口"""
        return self._config["websocket"]["port"]
    
    def get_backend_host(self) -> str:
        """获取后端主机"""
        return self._config["backend"]["host"]
    
    def get_frontend_host(self) -> str:
        """获取前端主机"""
        return self._config["frontend"]["host"]
    
    def get_backend_url(self) -> str:
        """获取后端完整URL"""
        return f"http://{self.get_backend_host()}:{self.get_backend_port()}"
    
    def get_frontend_url(self) -> str:
        """获取前端完整URL"""
        return f"http://{self.get_frontend_host()}:{self.get_frontend_port()}"
    
    def get_port_pool(self) -> list:
        """获取端口池"""
        pool_config = self._config["port_pool"]
        return list(range(pool_config["start"], pool_config["end"] + 1))
    
    def set_backend_port(self, port: int):
        """设置后端端口"""
        self._config["backend"]["port"] = port
        self.save_config()
    
    def set_frontend_port(self, port: int):
        """设置前端端口"""
        self._config["frontend"]["port"] = port
        self.save_config()
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0  # 0表示端口被占用
        except Exception:
            return False
    
    def find_available_port(self, start_port: int = None) -> int:
        """查找可用端口"""
        if start_port is None:
            start_port = self.get_backend_port()
        
        # 先检查配置的默认端口
        if self.is_port_available(start_port):
            return start_port
        
        # 在端口池中查找
        port_pool = self.get_port_pool()
        for port in port_pool:
            if self.is_port_available(port):
                return port
        
        # 如果端口池都被占用，从start_port开始递增查找
        port = start_port + 1
        while port < 65535:
            if self.is_port_available(port):
                return port
            port += 1
        
        raise RuntimeError("无法找到可用端口")


# 创建全局配置实例
ports_config = PortsConfig()


# 便捷函数
def get_backend_port() -> int:
    return ports_config.get_backend_port()


def get_frontend_port() -> int:
    return ports_config.get_frontend_port()


def get_backend_url() -> str:
    return ports_config.get_backend_url()


def get_frontend_url() -> str:
    return ports_config.get_frontend_url()


if __name__ == "__main__":
    # 测试配置
    print("=== 量化回测系统端口配置 ===")
    print(f"后端端口: {get_backend_port()}")
    print(f"前端端口: {get_frontend_port()}")
    print(f"后端URL: {get_backend_url()}")
    print(f"前端URL: {get_frontend_url()}")
    print(f"端口池: {ports_config.get_port_pool()[:5]}...") # 显示前5个
    
    # 创建配置文件
    ports_config.save_config()
    print(f"\n配置文件位置: {ports_config.config_file}")