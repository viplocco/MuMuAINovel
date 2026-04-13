"""物品分类预设服务 - 根据项目题材自动创建分类"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.item_category import ItemCategory
from app.logger import get_logger

logger = get_logger(__name__)


# 分类预设配置
CATEGORY_PRESETS = {
    # 通用分类（所有项目都有）
    "common": [
        {"name": "货币", "description": "通用交换媒介（金币、灵石、积分、信用点等）", "order": 1},
        {"name": "装备", "description": "可穿戴/使用的物品", "order": 2},
        {"name": "道具", "description": "功能性消耗品", "order": 3},
        {"name": "材料", "description": "用于合成/制作的素材", "order": 4},
        {"name": "特殊物品", "description": "剧情关键物品、传承物品", "order": 5},
    ],
    # 玄幻类
    "fantasy": [
        {"name": "法宝", "description": "修仙世界的法宝", "order": 10, "children": [
            {"name": "攻击法宝", "description": "用于攻击的法宝", "order": 1},
            {"name": "防御法宝", "description": "用于防御的法宝", "order": 2},
            {"name": "辅助法宝", "description": "辅助修行的法宝", "order": 3},
        ]},
        {"name": "丹药", "description": "各种丹药", "order": 20, "children": [
            {"name": "疗伤丹药", "description": "治疗伤势的丹药", "order": 1},
            {"name": "突破丹药", "description": "辅助境界突破的丹药", "order": 2},
            {"name": "辅助丹药", "description": "其他辅助效果的丹药", "order": 3},
        ]},
        {"name": "符箓", "description": "各种符箓", "order": 30},
        {"name": "典籍", "description": "功法秘籍、古籍", "order": 40},
        {"name": "灵兽", "description": "灵兽、妖兽相关", "order": 50},
    ],
    # 现代类
    "modern": [
        {"name": "武器", "description": "各类武器", "order": 10},
        {"name": "药品", "description": "现代药品", "order": 20},
        {"name": "电子设备", "description": "手机、电脑等电子设备", "order": 30},
        {"name": "文件证件", "description": "各类文件、证件", "order": 40},
        {"name": "交通工具", "description": "各类交通工具", "order": 50},
    ],
    # 科幻类
    "scifi": [
        {"name": "科技设备", "description": "高科技设备", "order": 10},
        {"name": "能源核心", "description": "各种能源装置", "order": 20},
        {"name": "合金材料", "description": "各种高级材料", "order": 30},
        {"name": "数据芯片", "description": "数据存储、AI芯片等", "order": 40},
        {"name": "星际导航", "description": "星际航行相关设备", "order": 50},
    ],
    # 历史类
    "historical": [
        {"name": "兵器", "description": "冷兵器、火器", "order": 10},
        {"name": "宝物", "description": "珍贵宝物", "order": 20},
        {"name": "官印信物", "description": "官印、令牌等信物", "order": 30},
        {"name": "古籍文书", "description": "古籍、文书", "order": 40},
        {"name": "珠宝首饰", "description": "珠宝、首饰", "order": 50},
    ],
}

# 项目题材到分类类型的映射（与 ATTRIBUTE_DEFINITIONS_BY_GENRE 保持一致）
GENRE_TO_CATEGORY_TYPE = {
    "修仙": "fantasy",
    "玄幻": "fantasy",
    "仙侠": "fantasy",
    "奇幻": "fantasy",
    "灵异": "fantasy",
    "武侠": "historical",
    "历史": "historical",
    "都市": "modern",
    "现代": "modern",
    "言情": "modern",
    "游戏": "modern",
    "悬疑": "modern",
    "科幻": "scifi",
    "末世": "scifi",
}


async def init_project_categories(
    db: AsyncSession,
    project_id: str,
    project_genre: str = None
) -> List[ItemCategory]:
    """
    初始化项目分类

    Args:
        db: 数据库会话
        project_id: 项目ID
        project_genre: 项目题材

    Returns:
        创建的分类列表
    """
    try:
        # 检查是否已有分类
        existing_query = select(ItemCategory).where(ItemCategory.project_id == project_id)
        result = await db.execute(existing_query)
        existing = result.scalars().first()

        if existing:
            logger.info(f"项目 {project_id} 已有分类，跳过初始化")
            return []

        created_categories = []

        # 确定题材类型
        category_type = GENRE_TO_CATEGORY_TYPE.get(project_genre, "fantasy") if project_genre else "fantasy"

        # 1. 创建通用分类
        common_presets = CATEGORY_PRESETS.get("common", [])
        for preset in common_presets:
            category = ItemCategory(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=preset["name"],
                description=preset.get("description", ""),
                parent_id=None,
                level=1,
                path=preset["name"],
                order_index=preset.get("order", 0),
                genre_type="common",
                is_system=True
            )
            db.add(category)
            created_categories.append(category)

        # 2. 创建题材特定分类
        genre_presets = CATEGORY_PRESETS.get(category_type, [])
        for preset in genre_presets:
            # 创建一级分类
            category = ItemCategory(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=preset["name"],
                description=preset.get("description", ""),
                parent_id=None,
                level=1,
                path=preset["name"],
                order_index=preset.get("order", 0),
                genre_type=category_type,
                is_system=True
            )
            db.add(category)
            created_categories.append(category)

            # 创建二级分类
            children = preset.get("children", [])
            for child in children:
                child_category = ItemCategory(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    name=child["name"],
                    description=child.get("description", ""),
                    parent_id=category.id,
                    level=2,
                    path=f"{preset['name']},{child['name']}",
                    order_index=child.get("order", 0),
                    genre_type=category_type,
                    is_system=True
                )
                db.add(child_category)
                created_categories.append(child_category)

        await db.commit()

        logger.info(f"项目 {project_id} 初始化分类成功，共创建 {len(created_categories)} 个分类")
        return created_categories

    except Exception as e:
        await db.rollback()
        logger.error(f"初始化项目分类失败: {str(e)}")
        raise


def get_suggested_category_for_item(
    item_name: str,
    item_type: str = None,
    description: str = None
) -> str:
    """
    根据物品信息推荐分类名称

    Args:
        item_name: 物品名称
        item_type: 物品类型
        description: 物品描述

    Returns:
        推荐的分类名称
    """
    # 类型关键词映射
    type_mapping = {
        "weapon": "武器",
        "armor": "装备",
        "consumable": "道具",
        "material": "材料",
        "artifact": "法宝",
        "pill": "丹药",
        "talisman": "符箓",
        "book": "典籍",
        "beast": "灵兽",
        "currency": "货币",
    }

    if item_type and item_type in type_mapping:
        return type_mapping[item_type]

    # 名称关键词映射
    name_lower = item_name.lower() if item_name else ""

    # 货币类
    currency_keywords = ["币", "钱", "金", "银", "灵石", "积分", "点数"]
    for kw in currency_keywords:
        if kw in name_lower:
            return "货币"

    # 丹药类
    pill_keywords = ["丹", "药", "丸", "散", "液", "剂"]
    for kw in pill_keywords:
        if kw in name_lower:
            return "丹药"

    # 法宝类
    artifact_keywords = ["剑", "刀", "枪", "棍", "杖", "扇", "镜", "鼎", "塔", "钟", "印", "符"]
    for kw in artifact_keywords:
        if kw in name_lower:
            return "法宝"

    # 典籍类
    book_keywords = ["经", "书", "典", "籍", "谱", "诀", "法"]
    for kw in book_keywords:
        if kw in name_lower:
            return "典籍"

    # 默认返回道具
    return "道具"