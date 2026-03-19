"""
修复 foreshadows 表缺少 title 列的问题

使用方法:
    python fix_foreshadows_title.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_engine, Base
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


async def fix_foreshadows_title():
    """为 foreshadows 表添加 title 列"""
    
    # 获取数据库引擎
    engine = await get_engine("local_21232f297a57a5a7")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            # 检查 title 列是否存在
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'foreshadows' AND column_name = 'title'
            """))
            
            exists = result.scalar_one_or_none()
            
            if exists:
                print("✅ foreshadows.title 列已存在，无需修复")
                return True
            
            print("⚠️  foreshadows.title 列不存在，开始添加...")
            
            # 添加 title 列
            await session.execute(text("""
                ALTER TABLE foreshadows 
                ADD COLUMN title VARCHAR(200) NOT NULL DEFAULT '未命名伏笔'
            """))
            
            await session.commit()
            
            print("✅ 成功添加 foreshadows.title 列")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 修复失败：{e}")
            raise


if __name__ == "__main__":
    print("🔧 开始修复 foreshadows 表...")
    asyncio.run(fix_foreshadows_title())
    print("✅ 修复完成")
