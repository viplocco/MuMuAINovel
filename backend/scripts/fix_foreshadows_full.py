"""
修复 foreshadows 表缺少的所有列

使用方法:
    python fix_foreshadows_full.py
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


async def check_and_add_column(session, table_name, column_name, column_def):
    """检查列是否存在，不存在则添加"""
    try:
        result = await session.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """))
        
        exists = result.scalar_one_or_none()
        
        if exists:
            print(f"  ✅ {table_name}.{column_name} 已存在")
            return False
        
        print(f"  ⚠️  {table_name}.{column_name} 不存在，开始添加...")
        
        # 添加列
        await session.execute(text(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} {column_def}
        """))
        
        print(f"  ✅ 成功添加 {table_name}.{column_name}")
        return True
        
    except Exception as e:
        print(f"  ❌ 添加 {table_name}.{column_name} 失败: {e}")
        raise


async def fix_foreshadows_table():
    """为 foreshadows 表添加所有缺失的列"""
    
    # 获取数据库引擎
    engine = await get_engine("local_21232f297a57a5a7")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            print("🔧 开始检查并修复 foreshadows 表...")
            
            # 定义所有需要的列及其类型
            columns_to_check = [
                ("title", "VARCHAR(200) NOT NULL DEFAULT '未命名伏笔'"),
                ("content", "TEXT NOT NULL DEFAULT ''"),
                ("hint_text", "TEXT"),
                ("resolution_text", "TEXT"),
                ("source_type", "VARCHAR(20) DEFAULT 'manual'"),
                ("source_memory_id", "VARCHAR(100)"),
                ("source_analysis_id", "VARCHAR(36)"),
                ("plant_chapter_id", "VARCHAR(36)"),
                ("plant_chapter_number", "INTEGER"),
                ("target_resolve_chapter_id", "VARCHAR(36)"),
                ("target_resolve_chapter_number", "INTEGER"),
                ("actual_resolve_chapter_id", "VARCHAR(36)"),
                ("actual_resolve_chapter_number", "INTEGER"),
                ("status", "VARCHAR(20) DEFAULT 'pending'"),
                ("is_long_term", "BOOLEAN DEFAULT FALSE"),
                ("importance", "FLOAT DEFAULT 0.5"),
                ("strength", "INTEGER DEFAULT 5"),
                ("subtlety", "INTEGER DEFAULT 5"),
                ("urgency", "INTEGER DEFAULT 0"),
                ("related_characters", "JSON"),
                ("related_foreshadow_ids", "JSON"),
                ("tags", "JSON"),
                ("category", "VARCHAR(50)"),
                ("notes", "TEXT"),
                ("resolution_notes", "TEXT"),
                ("auto_remind", "BOOLEAN DEFAULT TRUE"),
                ("remind_before_chapters", "INTEGER DEFAULT 5"),
                ("include_in_context", "BOOLEAN DEFAULT TRUE"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("planted_at", "TIMESTAMP"),
                ("resolved_at", "TIMESTAMP"),
            ]
            
            added_count = 0
            for column_name, column_def in columns_to_check:
                added = await check_and_add_column(session, "foreshadows", column_name, column_def)
                if added:
                    added_count += 1
            
            await session.commit()
            
            print(f"\n✅ 修复完成！共添加 {added_count} 个列")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ 修复失败：{e}")
            raise


if __name__ == "__main__":
    asyncio.run(fix_foreshadows_table())
