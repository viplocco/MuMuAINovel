"""
清理 foreshadows 表结构 - 删除旧列，保留新列

使用方法:
    python cleanup_foreshadows.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


async def cleanup_foreshadows():
    """清理 foreshadows 表，删除旧列"""
    
    engine = await get_engine("local_21232f297a57a5a7")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # 需要删除的旧列（与新模型不兼容的列）
    old_columns = [
        "name",           # 旧版使用 name，新版使用 title
        "description",    # 旧版使用 description，新版使用 content
        "foreshadow_type", # 旧版字段
        "resolve_chapter_number",  # 旧版字段，新版使用 target_resolve_chapter_number 和 actual_resolve_chapter_number
        "resolve_chapter_id",      # 旧版字段
        "resolve_description",     # 旧版字段，新版使用 resolution_text
        "plant_position",          # 旧版字段
        "user_id",                 # 旧版字段，应该使用 project 关联
        "ai_generated",            # 旧版字段
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            print("🔧 开始清理 foreshadows 表...")
            
            # 获取现有列
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'foreshadows'
            """))
            existing_columns = [row[0] for row in result.all()]
            print(f"现有列: {existing_columns}")
            
            # 删除旧列
            dropped = []
            for col in old_columns:
                if col in existing_columns:
                    try:
                        print(f"  🗑️  删除旧列: {col}")
                        await session.execute(text(f'ALTER TABLE foreshadows DROP COLUMN IF EXISTS "{col}"'))
                        dropped.append(col)
                    except Exception as e:
                        print(f"  ⚠️  删除 {col} 失败: {e}")
            
            await session.commit()
            
            if dropped:
                print(f"\n✅ 已删除 {len(dropped)} 个旧列: {dropped}")
            else:
                print("\n✅ 没有需要删除的旧列")
            
            # 再次检查列
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'foreshadows'
            """))
            remaining_columns = [row[0] for row in result.all()]
            print(f"\n剩余列 ({len(remaining_columns)} 个):")
            for col in sorted(remaining_columns):
                print(f"  - {col}")
                
        except Exception as e:
            await session.rollback()
            print(f"\n❌ 清理失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(cleanup_foreshadows())
