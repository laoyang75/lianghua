"""
共享配置管理
避免多处硬编码端口号等配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent
        
        self.project_root = project_root
        self.config_file = project_root / "service_config.json"
        self._config = self._load_default_config()
        self.load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "backend": {
                "host": "127.0.0.1",
                "port": 5318,
                "debug": False,
                "auto_restart": False,
                "log_level": "INFO"
            },
            "frontend": {
                "port": 5173,
                "auto_start": False
            },
            "database": {
                "path": os.path.expanduser("~/AppData/Roaming/QuantBacktest/data/data.duckdb") if os.name == 'nt' 
                       else os.path.expanduser("~/.local/share/QuantBacktest/data.duckdb")
            },
            "logging": {
                "level": "INFO",
                "max_files": 7,
                "max_size_mb": 10
            },
            "monitoring": {
                "check_interval": 10,
                "restart_max_attempts": 3,
                "health_timeout": 30
            }
        }
    
    def load_config(self):
        """从文件加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # 深度合并配置
                    self._deep_merge(self._config, file_config)
            except Exception as e:
                print(f"警告：加载配置文件失败，使用默认配置: {e}")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"错误：保存配置文件失败: {e}")
    
    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分路径如 'backend.port'"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = True):
        """设置配置值"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        if save:
            self.save_config()
    
    @property
    def backend(self) -> Dict[str, Any]:
        """获取后端配置"""
        return self._config.get("backend", {})
    
    @property
    def frontend(self) -> Dict[str, Any]:
        """获取前端配置"""
        return self._config.get("frontend", {})
    
    @property
    def database(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self._config.get("database", {})
    
    @property
    def logging(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self._config.get("logging", {})
    
    @property
    def monitoring(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self._config.get("monitoring", {})
    
    def get_backend_url(self) -> str:
        """获取后端服务URL"""
        backend = self.backend
        return f"http://{backend.get('host', '127.0.0.1')}:{backend.get('port', 5318)}"
    
    def get_frontend_url(self) -> str:
        """获取前端服务URL"""
        frontend = self.frontend
        return f"http://localhost:{frontend.get('port', 5173)}"


# 全局配置实例
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_backend_port() -> int:
    """获取后端端口"""
    return get_config().get('backend.port', 5318)


def get_frontend_port() -> int:
    """获取前端端口"""
    return get_config().get('frontend.port', 5173)


def get_backend_url() -> str:
    """获取后端URL"""
    return get_config().get_backend_url()


def get_frontend_url() -> str:
    """获取前端URL"""
    return get_config().get_frontend_url()


if __name__ == "__main__":
    # 测试配置管理器
    config = get_config()
    print("Backend URL:", config.get_backend_url())
    print("Frontend URL:", config.get_frontend_url())
    print("Database path:", config.get('database.path'))
    
    # 测试设置配置
    config.set('backend.port', 5319)
    print("New backend URL:", config.get_backend_url())