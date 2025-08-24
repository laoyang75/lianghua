"""
DuckDB 数据库管理模块
"""

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import polars as pl
from loguru import logger

from .config import settings


class DatabaseManager:
    """DuckDB 数据库管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = asyncio.Lock()
        
    async def connect(self):
        """连接数据库"""
        if self.conn is None:
            try:
                self.conn = duckdb.connect(self.db_path)
                logger.info(f"已连接到数据库: {self.db_path}")
            except Exception as e:
                logger.error(f"连接数据库失败: {e}")
                raise
    
    async def disconnect(self):
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("已断开数据库连接")
    
    def close(self):
        """同步关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    async def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """执行SQL查询"""
        async with self._lock:
            if not self.conn:
                await self.connect()
            
            try:
                if params:
                    result = self.conn.execute(query, params)
                else:
                    result = self.conn.execute(query)
                return result.fetchall()
            except Exception as e:
                logger.error(f"执行查询失败: {query}, 错误: {e}")
                raise
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """批量执行SQL"""
        async with self._lock:
            if not self.conn:
                await self.connect()
            
            try:
                self.conn.executemany(query, params_list)
            except Exception as e:
                logger.error(f"批量执行失败: {query}, 错误: {e}")
                raise
    
    async def query_df(self, query: str, params: Optional[tuple] = None) -> pl.DataFrame:
        """查询并返回Polars DataFrame"""
        async with self._lock:
            if not self.conn:
                await self.connect()
            
            try:
                if params:
                    result = self.conn.execute(query, params)
                else:
                    result = self.conn.execute(query)
                
                # 转换为Polars DataFrame
                columns = [desc[0] for desc in result.description]
                data = result.fetchall()
                
                if not data:
                    return pl.DataFrame(schema={col: pl.String for col in columns})
                
                return pl.DataFrame(data, schema=columns)
            except Exception as e:
                logger.error(f"查询DataFrame失败: {query}, 错误: {e}")
                raise
    
    async def insert_df(self, table_name: str, df: pl.DataFrame, if_exists: str = "append"):
        """插入Polars DataFrame到表"""
        async with self._lock:
            if not self.conn:
                await self.connect()
            
            try:
                # 将Polars DataFrame转换为Arrow Table然后插入
                arrow_table = df.to_arrow()
                
                if if_exists == "replace":
                    self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                self.conn.register("temp_df", arrow_table)
                
                # 根据不同模式处理数据插入
                if if_exists == "upsert" and table_name == "prices_daily":
                    # 对于股价数据，使用 INSERT OR REPLACE 语法避免重复键错误
                    # DuckDB 使用 INSERT OR REPLACE 而不是 ON CONFLICT
                    self.conn.execute(f"""
                        INSERT OR REPLACE INTO {table_name} 
                        SELECT * FROM temp_df
                    """)
                else:
                    # 默认插入模式
                    self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
                
                self.conn.unregister("temp_df")
                
                logger.debug(f"插入{len(df)}行数据到表 {table_name}")
            except Exception as e:
                logger.error(f"插入DataFrame失败: {table_name}, 错误: {e}")
                raise


# 全局数据库管理器实例，添加线程锁保证并发安全
_db_manager: Optional[DatabaseManager] = None
_db_manager_lock = asyncio.Lock()


async def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（线程安全，异步版本）"""
    global _db_manager
    if _db_manager is None:
        async with _db_manager_lock:
            # 双重检查锁定模式
            if _db_manager is None:
                _db_manager = DatabaseManager(settings.DATABASE_URL)
    return _db_manager


def get_db_manager_sync() -> DatabaseManager:
    """获取数据库管理器实例（同步版本，用于向后兼容）"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(settings.DATABASE_URL)
    return _db_manager


async def init_database():
    """初始化数据库"""
    db = await get_db_manager()
    await db.connect()
    
    try:
        # 获取当前schema版本（检查是否需要首次初始化）
        current_version = await get_schema_version()
        
        # 如果是全新数据库，执行自动备份
        if current_version == 0:
            logger.info("检测到新数据库，开始初始化...")
        else:
            logger.info(f"检测到已存在的数据库，当前schema版本: {current_version}")
            # 执行升级前备份
            try:
                await backup_database()
            except Exception as e:
                logger.warning(f"升级前备份失败，将继续初始化: {e}")
        
        # 创建schema版本表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        
        # 创建价格数据表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prices_daily (
                date DATE NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                adj_close DOUBLE,
                calendar_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            )
        """)
        
        # 创建标签定义表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                name VARCHAR(200) PRIMARY KEY,
                rule VARCHAR(100) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建标签股票表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS label_stocks (
                label_name VARCHAR(200) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                rank INTEGER NOT NULL,
                score DOUBLE,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (label_name, symbol)
            )
        """)
        
        # 创建旧标签数据表（保持兼容性）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS labels_old (
                trade_date DATE NOT NULL,
                label_name VARCHAR(100) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                score DOUBLE,
                rank INTEGER,
                meta_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (trade_date, label_name, rank)
            )
        """)
        
        # 创建实验记录表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id VARCHAR(50) PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                strategy_name VARCHAR(100) NOT NULL,
                label_name VARCHAR(100) NOT NULL,
                cfg_json JSON NOT NULL,
                metrics_json JSON NOT NULL,
                result_hash VARCHAR(64) NOT NULL,
                deleted_at TIMESTAMP
            )
        """)
        
        # 创建任务表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR(50) PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'queued',
                progress INTEGER DEFAULT 0,
                message TEXT,
                payload_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                error_message TEXT
            )
        """)
        
        # 创建优化索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_prices_daily_date ON prices_daily(date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_prices_daily_symbol ON prices_daily(symbol)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_prices_daily_symbol_date ON prices_daily(symbol, date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_labels_start_date ON labels(start_date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_labels_end_date ON labels(end_date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_labels_name ON labels(name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_labels_rule ON labels(rule)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_experiments_strategy ON experiments(strategy_name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
        
        # 应用schema版本升级
        await apply_schema_migrations(current_version)
        
        # 验证数据库完整性
        await validate_database_integrity()
        
        logger.info("数据库初始化/升级完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def get_schema_version() -> int:
    """获取当前schema版本"""
    db = await get_db_manager()
    try:
        result = await db.execute("SELECT MAX(version) FROM schema_version")
        version = result[0][0] if result and result[0][0] is not None else 0
        return version
    except:
        return 0


async def backup_database():
    """备份数据库"""
    try:
        source_path = Path(settings.DATABASE_URL)
        if not source_path.exists():
            logger.warning("数据库文件不存在，跳过备份")
            return
        
        # 确保备份目录存在
        settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        # 创建备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"data_{timestamp}.duckdb"
        backup_path = settings.BACKUP_DIR / backup_filename
        
        # 复制数据库文件
        shutil.copy2(source_path, backup_path)
        logger.info(f"数据库备份完成: {backup_path}")
        
        # 清理旧备份（保留最近N个）
        await cleanup_old_backups()
        
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"数据库备份失败: {e}")
        raise


async def cleanup_old_backups():
    """清理旧的备份文件"""
    try:
        backup_files = list(settings.BACKUP_DIR.glob("data_*.duckdb"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 删除多余的备份文件
        for old_backup in backup_files[settings.DATABASE_BACKUP_COUNT:]:
            old_backup.unlink()
            logger.debug(f"删除旧备份: {old_backup}")
            
    except Exception as e:
        logger.error(f"清理备份文件失败: {e}")


async def get_database_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    db = await get_db_manager()
    
    try:
        # 获取各表的记录数
        stats = {}
        
        # 价格数据统计
        result = await db.execute("SELECT COUNT(*) FROM prices_daily")
        stats['prices_daily_count'] = result[0][0]
        
        result = await db.execute("SELECT COUNT(DISTINCT symbol) FROM prices_daily")
        stats['unique_symbols'] = result[0][0]
        
        result = await db.execute("SELECT MIN(date), MAX(date) FROM prices_daily")
        if result and result[0][0]:
            stats['date_range'] = {
                'start': result[0][0].isoformat(),
                'end': result[0][1].isoformat()
            }
        
        # 标签数据统计
        result = await db.execute("SELECT COUNT(*) FROM labels")
        stats['labels_count'] = result[0][0]
        
        result = await db.execute("SELECT COUNT(DISTINCT name) FROM labels")
        stats['unique_labels'] = result[0][0]
        
        # 实验统计
        result = await db.execute("SELECT COUNT(*) FROM experiments WHERE deleted_at IS NULL")
        stats['experiments_count'] = result[0][0]
        
        # 任务统计
        result = await db.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        stats['task_status'] = {row[0]: row[1] for row in result}
        
        # 数据库文件大小
        db_path = Path(settings.DATABASE_URL)
        if db_path.exists():
            stats['db_file_size'] = db_path.stat().st_size
        
        return stats
        
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        return {}


async def apply_schema_migrations(current_version: int):
    """应用数据库schema迁移"""
    db = await get_db_manager()
    target_version = 1  # 当前最新版本
    
    if current_version >= target_version:
        logger.info(f"Schema版本已是最新: {current_version}")
        return
    
    try:
        # 版本1: 基础schema
        if current_version < 1:
            await db.execute("""
                INSERT INTO schema_version (version, description) 
                VALUES (1, '初始数据库结构')
            """)
            logger.info("应用Schema迁移: 版本 0 -> 1")
        
        # 未来可添加更多迁移
        # if current_version < 2:
        #     await db.execute("ALTER TABLE ... ADD COLUMN ...")
        #     await db.execute("INSERT INTO schema_version (version, description) VALUES (2, '添加新字段')")
        #     logger.info("应用Schema迁移: 版本 1 -> 2")
        
        final_version = await get_schema_version()
        logger.info(f"Schema迁移完成，当前版本: {final_version}")
        
    except Exception as e:
        logger.error(f"Schema迁移失败: {e}")
        raise


async def validate_database_integrity():
    """验证数据库完整性"""
    db = await get_db_manager()
    
    try:
        # 检查必需的表是否存在（使用DuckDB语法）
        required_tables = ['schema_version', 'prices_daily', 'labels', 'experiments', 'tasks']
        for table in required_tables:
            try:
                result = await db.execute(f"SELECT 1 FROM {table} LIMIT 0")
                logger.debug(f"表 {table} 存在")
            except Exception:
                raise ValueError(f"必需的表 {table} 不存在")
        
        # 检查关键索引是否能正常工作（DuckDB会自动优化查询）
        test_queries = [
            ("SELECT COUNT(*) FROM prices_daily WHERE date > '2020-01-01'", "价格数据按日期查询"),
            ("SELECT COUNT(*) FROM labels WHERE name = 'test'", "标签数据按名称查询"),
            ("SELECT COUNT(*) FROM experiments WHERE created_at > '2020-01-01'", "实验数据按创建时间查询")
        ]
        
        for query, desc in test_queries:
            try:
                await db.execute(query)
                logger.debug(f"索引测试通过: {desc}")
            except Exception as e:
                logger.warning(f"索引测试失败 ({desc}): {e}")
        
        logger.info("数据库完整性验证通过")
        
    except Exception as e:
        logger.error(f"数据库完整性验证失败: {e}")
        raise


async def restore_database_from_backup(backup_path: str):
    """从备份恢复数据库"""
    try:
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        # 关闭当前数据库连接
        db = await get_db_manager()
        await db.disconnect()
        
        # 备份当前数据库（以防恢复失败）
        current_db_path = Path(settings.DATABASE_URL)
        if current_db_path.exists():
            recovery_backup = current_db_path.parent / f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.duckdb"
            shutil.copy2(current_db_path, recovery_backup)
            logger.info(f"当前数据库已备份到: {recovery_backup}")
        
        # 恢复备份
        shutil.copy2(backup_file, current_db_path)
        logger.info(f"数据库已从备份恢复: {backup_path}")
        
        # 重新连接并验证
        await db.connect()
        await validate_database_integrity()
        
        return True
        
    except Exception as e:
        logger.error(f"数据库恢复失败: {e}")
        raise