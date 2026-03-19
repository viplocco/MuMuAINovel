#!/usr/bin/env python3
"""
重置用户密码脚本
用于解决本地登录失败的问题
"""
import asyncio
import sys
import os

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
sys.path.insert(0, backend_dir)

from sqlalchemy import select, Column, String, Boolean, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import hashlib
from datetime import datetime

# 创建基础模型
Base = declarative_base()


class UserPassword(Base):
    """用户密码模型"""
    __tablename__ = "user_passwords"

    user_id = Column(String(100), primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(64), nullable=False)
    has_custom_password = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


def get_database_url():
    """从 .env 读取数据库 URL"""
    env_path = os.path.join(backend_dir, '.env')
    database_url = "postgresql+asyncpg://neondb_owner:npg_QBEd2wHC0FsM@ep-mute-mud-a495xzkk-pooler.us-east-1.aws.neon.tech:5432/neondb"

    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL='):
                    database_url = line.split('=', 1)[1].strip()
                    break

    return database_url


def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


async def reset_password(user_id: str, new_password: str, database_url: str):
    """重置用户密码"""
    engine = create_async_engine(database_url, echo=False)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserPassword).where(UserPassword.user_id == user_id)
        )
        pwd_record = result.scalar_one_or_none()

        if pwd_record:
            pwd_record.password_hash = hash_password(new_password)
            pwd_record.has_custom_password = False
            print(f"✅ 已更新用户 {user_id} 的密码")
        else:
            pwd_record = UserPassword(
                user_id=user_id,
                username="admin",
                password_hash=hash_password(new_password),
                has_custom_password=False,
            )
            session.add(pwd_record)
            print(f"✅ 已为用户 {user_id} 创建密码记录")

        await session.commit()

    await engine.dispose()


async def list_users(database_url: str):
    """列出所有有密码的用户"""
    engine = create_async_engine(database_url, echo=False)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        result = await session.execute(select(UserPassword))
        records = result.scalars().all()

        print("\n📋 数据库中的用户密码记录:")
        if not records:
            print("  (无记录)")
        for r in records:
            print(f"  - user_id: {r.user_id}, username: {r.username}, has_custom: {r.has_custom_password}")

    await engine.dispose()


async def main():
    target_user_id = "local_21232f297a57a5a7"
    default_password = "admin123"

    print("=" * 50)
    print("MuMuAINovel 密码重置工具")
    print("=" * 50)

    database_url = get_database_url()
    print(f"\n数据库: {database_url[:60]}...")

    await list_users(database_url)

    print("\n开始重置密码...")
    await reset_password(target_user_id, default_password, database_url)

    print("\n" + "=" * 50)
    print("重置成功!")
    print("=" * 50)
    print("\n请使用以下凭据登录:")
    print(f"  用户名: admin")
    print(f"  密码: {default_password}")


if __name__ == "__main__":
    asyncio.run(main())