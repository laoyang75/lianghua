"""
pytest配置和测试fixture
"""

import asyncio
import pytest
import os
import sys
from pathlib import Path

# 将项目根目录加入Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """测试数据库fixture"""
    # 使用内存数据库进行测试
    from app.core.database import DatabaseManager
    
    db = DatabaseManager(":memory:")
    await db.init_database()
    yield db
    db.close()


@pytest.fixture
def client():
    """测试客户端fixture"""
    from fastapi.testclient import TestClient
    from app.main import create_app
    
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client