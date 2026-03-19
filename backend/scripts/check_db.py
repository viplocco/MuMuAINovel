"""检查数据库配置"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def check():
    engine = await get_engine('local_21232f297a57a5a7')
    print(f'数据库引擎: {engine}')
    print(f'数据库URL: {engine.url}')
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # 检查表是否存在
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'foreshadows'
        """))
        table = result.scalar_one_or_none()
        print(f'foreshadows 表存在: {table is not None}')
        
        if table:
            # 检查列
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'foreshadows'
            """))
            columns = result.all()
            print(f'现有列数: {len(columns)}')
            for col in columns:
                print(f'  - {col[0]}: {col[1]}')
        else:
            print('表不存在，可能是 SQLite 数据库')
            # 尝试直接查询
            try:
                result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='foreshadows'"))
                table = result.scalar_one_or_none()
                print(f'SQLite foreshadows 表存在: {table is not None}')
                
                if table:
                    result = await session.execute(text("PRAGMA table_info(foreshadows)"))
                    columns = result.all()
                    print(f'SQLite 列数: {len(columns)}')
                    for col in columns:
                        print(f'  - {col[1]}: {col[2]}')
            except Exception as e:
                print(f'SQLite 检查失败: {e}')

if __name__ == "__main__":
    asyncio.run(check())
