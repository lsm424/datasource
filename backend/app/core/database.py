from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import asyncio
from typing import AsyncGenerator

from app.core.config import settings

# 创建数据库引擎
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite 特殊配置
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        connect_args={
            "check_same_thread": False,
            "timeout": 20,
        },
        poolclass=StaticPool,
    )
else:
    # 其他数据库配置
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
    )

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 创建基础模型类
Base = declarative_base()

# 元数据对象
metadata = MetaData()


def get_db() -> Session:
    """获取数据库会话（同步版本）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db_async() -> AsyncGenerator[Session, None]:
    """获取数据库会话（异步版本）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database():
    """创建数据库文件（仅用于SQLite）"""
    if settings.DATABASE_URL.startswith("sqlite"):
        import sqlite3
        import os
        
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.close()
            print(f"Created SQLite database: {db_path}")


async def create_tables():
    """创建所有表"""
    # 确保数据库存在
    create_database()
    
    # 导入所有模型以确保它们被注册
    from app.models import user, datasource  # noqa
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def drop_tables():
    """删除所有表（谨慎使用）"""
    Base.metadata.drop_all(bind=engine)
    print("All database tables dropped")


def get_engine():
    """获取数据库引擎"""
    return engine


def get_session() -> Session:
    """直接获取会话实例"""
    return SessionLocal()


# 数据库健康检查
def check_database_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
