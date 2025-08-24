"""
应用配置管理
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """应用配置类"""
    
    def __init__(self):
        # 基础配置
        self.DEBUG: bool = False
        self.HOST: str = "127.0.0.1"
        self.PORT: int = 5317
        self.VERSION: str = "1.0.0"
        
        # 路径配置
        self.BASE_DIR = Path(__file__).parent.parent.parent
        self.PROJECT_ROOT = self.BASE_DIR.parent
        
        # 数据目录配置
        if os.name == 'nt':  # Windows
            self.USER_DATA_DIR = Path(os.getenv('APPDATA')) / 'QuantBacktest'
        else:  # macOS/Linux
            self.USER_DATA_DIR = Path.home() / '.quant-backtest'
        
        self.DATA_DIR = self.USER_DATA_DIR / 'data'
        self.LOG_DIR = self.USER_DATA_DIR / 'logs'
        self.BACKUP_DIR = self.USER_DATA_DIR / 'backup'
        self.EXPORT_DIR = self.USER_DATA_DIR / 'exports'
        
        # 确保目录存在
        for dir_path in [self.DATA_DIR, self.LOG_DIR, self.BACKUP_DIR, self.EXPORT_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 数据库配置
        self.DATABASE_URL = str(self.DATA_DIR / 'data.duckdb')
        self.DATABASE_BACKUP_COUNT = 7  # 保留最近7天的备份
        
        # 任务配置
        self.MAX_CONCURRENT_TASKS = 3
        self.TASK_TIMEOUT = 3600  # 1小时超时
        
        # yfinance 配置
        self.YFINANCE_TIMEOUT = 30
        self.YFINANCE_BATCH_SIZE = 100
        self.YFINANCE_MAX_RETRIES = 3
        
        # 回测配置
        self.BACKTEST_MAX_SYMBOLS = 10000
        self.BACKTEST_MAX_DAYS = 3650  # 10年
        
        # 缓存配置
        self.CACHE_TTL = 3600  # 1小时缓存
        
        # 安全配置
        self.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


# 全局配置实例
settings = Settings()


def get_database_url() -> str:
    """获取数据库连接URL"""
    return settings.DATABASE_URL


def get_data_dir() -> Path:
    """获取数据目录"""
    return settings.DATA_DIR


def get_log_dir() -> Path:
    """获取日志目录"""
    return settings.LOG_DIR


def get_backup_dir() -> Path:
    """获取备份目录"""
    return settings.BACKUP_DIR


def get_export_dir() -> Path:
    """获取导出目录"""
    return settings.EXPORT_DIR


def is_debug() -> bool:
    """是否调试模式"""
    return settings.DEBUG