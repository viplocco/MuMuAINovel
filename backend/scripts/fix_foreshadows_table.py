"""
修复 foreshadows 表结构 - 添加缺失的 title 字段

问题：数据库中 foreshadows 表缺少 title 字段，导致查询失败
"""
import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import DATABASE_URL

# 创建同步引擎用于修复 (Neon PostgreSQL)
# 使用 psycopg2 作为同步驱动
sync_engine = create_engine(
    DATABASE_URL.replace('+asyncpg', '+psycopg2'),
    connect_args={'sslmode': 'require'}
)


def fix_foreshadows_table():
    """检查并修复 foreshadows 表结构"""
    with sync_engine.begin() as conn:
        # 检查 title 字段是否存在
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'foreshadows' AND column_name = 'title'
        """
        result = conn.execute(text(check_sql))
        has_title = result.fetchone() is not None
        
        if has_title:
            print("✅ foreshadows.title 字段已存在，无需修复")
            return
        
        print("⚠️ 发现 foreshadows 表缺少 title 字段，正在添加...")
        
        # 添加 title 字段
        alter_sql = """
        ALTER TABLE foreshadows 
        ADD COLUMN title VARCHAR(200) NOT NULL DEFAULT '未命名伏笔'
        """
        conn.execute(text(alter_sql))
        
        # 检查其他可能缺失的字段
        required_columns = [
            ('hint_text', 'TEXT', None),
            ('resolution_text', 'TEXT', None),
            ('source_type', 'VARCHAR(20)', 'manual'),
            ('source_memory_id', 'VARCHAR(100)', None),
            ('source_analysis_id', 'VARCHAR(36)', None),
            ('plant_chapter_id', 'VARCHAR(36)', None),
            ('plant_chapter_number', 'INTEGER', None),
            ('target_resolve_chapter_id', 'VARCHAR(36)', None),
            ('target_resolve_chapter_number', 'INTEGER', None),
            ('actual_resolve_chapter_id', 'VARCHAR(36)', None),
            ('actual_resolve_chapter_number', 'INTEGER', None),
            ('is_long_term', 'BOOLEAN', 'false'),
            ('importance', 'FLOAT', '0.5'),
            ('strength', 'INTEGER', '5'),
            ('subtlety', 'INTEGER', '5'),
            ('urgency', 'INTEGER', '0'),
            ('related_characters', 'JSON', None),
            ('related_foreshadow_ids', 'JSON', None),
            ('tags', 'JSON', None),
            ('category', 'VARCHAR(50)', None),
            ('notes', 'TEXT', None),
            ('resolution_notes', 'TEXT', None),
            ('auto_remind', 'BOOLEAN', 'true'),
            ('remind_before_chapters', 'INTEGER', '5'),
            ('include_in_context', 'BOOLEAN', 'true'),
            ('planted_at', 'TIMESTAMP', None),
            ('resolved_at', 'TIMESTAMP', None),
        ]
        
        for col_name, col_type, default_val in required_columns:
            check_col_sql = f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'foreshadows' AND column_name = '{col_name}'
            """
            result = conn.execute(text(check_col_sql))
            if result.fetchone() is None:
                default_clause = f"DEFAULT {default_val}" if default_val else ""
                alter_col_sql = f"""
                ALTER TABLE foreshadows 
                ADD COLUMN {col_name} {col_type} {default_clause}
                """
                conn.execute(text(alter_col_sql))
                print(f"  ✅ 添加字段: {col_name}")
        
        print("✅ foreshadows 表修复完成")


def check_prompt_templates():
    """检查 prompt_templates 表是否存在"""
    with sync_engine.begin() as conn:
        check_sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'prompt_templates'
        )
        """
        result = conn.execute(text(check_sql))
        exists = result.scalar()
        
        if exists:
            print("✅ prompt_templates 表已存在")
        else:
            print("⚠️ prompt_templates 表不存在，需要运行数据库迁移")
            print("   请执行: alembic upgrade head")


def main():
    print("=" * 60)
    print("MuMuAINovel 数据库修复工具")
    print("=" * 60)
    
    try:
        fix_foreshadows_table()
        check_prompt_templates()
        print("\n✅ 所有检查和修复已完成")
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
