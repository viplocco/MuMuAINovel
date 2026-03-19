"""
修复 Neon 数据库缺失字段问题

问题：foreshadows 表缺少 title 字段
执行：cd backend && .venv\Scripts\python.exe scripts\fix_neon_db.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.config import DATABASE_URL


async def fix_database():
    """修复数据库缺失字段"""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # 创建异步引擎
    engine = create_async_engine(DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            print("=" * 60)
            print("MuMuAINovel 数据库修复工具")
            print("=" * 60)
            
            # 1. 检查并修复 foreshadows.title 字段
            print("\n📋 检查 foreshadows.title 字段...")
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'foreshadows' AND column_name = 'title'
            """
            result = await conn.execute(text(check_sql))
            has_title = result.fetchone() is not None
            
            if has_title:
                print("✅ foreshadows.title 字段已存在")
            else:
                print("⚠️  发现 foreshadows 表缺少 title 字段，正在添加...")
                alter_sql = """
                ALTER TABLE foreshadows 
                ADD COLUMN title VARCHAR(200) NOT NULL DEFAULT '未命名伏笔'
                """
                await conn.execute(text(alter_sql))
                print("✅ 已添加 foreshadows.title 字段")
            
            # 2. 检查 prompt_templates 表
            print("\n📋 检查 prompt_templates 表...")
            check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'prompt_templates'
            )
            """
            result = await conn.execute(text(check_table_sql))
            exists = result.scalar()
            
            if exists:
                print("✅ prompt_templates 表已存在")
            else:
                print("⚠️  prompt_templates 表不存在")
                print("   请运行：alembic upgrade head")
            
            print("\n" + "=" * 60)
            print("✅ 数据库修复完成")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ 修复失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(fix_database())
    sys.exit(0 if success else 1)
