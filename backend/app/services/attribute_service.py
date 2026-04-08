"""能力属性服务 - 动态能力值计算和管理"""
from typing import Dict, Any, List, Optional
import json
from app.constants.attribute_definitions import (
    ATTRIBUTE_DEFINITIONS_BY_GENRE,
    DEFAULT_ATTRIBUTES,
    SPIRITUAL_ROOT_QUALITY,
)
from app.logger import get_logger

logger = get_logger(__name__)


class AttributeService:
    """能力属性服务 - 管理动态能力系统"""

    @staticmethod
    def get_attribute_schema_for_genre(genre: str) -> Dict:
        """
        获取指定小说类型的属性定义

        Args:
            genre: 小说类型

        Returns:
            属性定义字典
        """
        return ATTRIBUTE_DEFINITIONS_BY_GENRE.get(genre, DEFAULT_ATTRIBUTES)

    @staticmethod
    def calculate_combo_quality(
        attr_config: Dict,
        selected_elements: List[str]
    ) -> Dict:
        """
        计算组合属性的品质（如灵根品质）

        Args:
            attr_config: 属性配置
            selected_elements: 选中的元素列表

        Returns:
            包含品质信息的属性值字典
        """
        if attr_config.get("quality_config"):
            count = len(selected_elements)
            quality_config = attr_config["quality_config"]
            # 查找最接近的品质（元素数量越少品质越高）
            quality = quality_config.get(count)
            if quality:
                return {
                    "type": "combo_select",
                    "elements": selected_elements,
                    "quality": quality["name"],
                    "rank": quality["rank"],
                    "growth_rate": quality["growth_rate"]
                }
            # 超出配置范围，使用最低品质
            max_count = max(quality_config.keys())
            if count > max_count:
                lowest_quality = quality_config[max_count]
                return {
                    "type": "combo_select",
                    "elements": selected_elements[:max_count],  # 截断到最大数量
                    "quality": lowest_quality["name"],
                    "rank": lowest_quality["rank"],
                    "growth_rate": lowest_quality["growth_rate"]
                }
        return {
            "type": "combo_select",
            "elements": selected_elements
        }

    @staticmethod
    def calculate_initial_attributes(
        attribute_schema: Dict,
        career_base_attributes: Optional[Dict] = None,
        stage: int = 1,
        role_type: str = 'supporting'
    ) -> Dict[str, Any]:
        """
        根据项目属性定义和职业配置计算初始能力值

        Args:
            attribute_schema: 项目的属性定义
            career_base_attributes: 职业的基础能力配置
            stage: 初始阶段
            role_type: 角色类型（主角有额外加成）

        Returns:
            初始化的能力值字典
        """
        if isinstance(attribute_schema, str):
            attribute_schema = json.loads(attribute_schema)

        result = {}
        attributes_config = attribute_schema.get("attributes", {})

        for attr_name, attr_config in attributes_config.items():
            attr_type = attr_config.get("type", "numeric")

            if attr_type == "stage":
                # 阶段型: 设置初始阶段
                stages = attr_config.get("stages", [])
                stage_index = max(1, min(stage, len(stages)))
                result[attr_name] = {
                    "type": "stage",
                    "value": stage_index,
                    "name": stages[stage_index - 1] if stages else f"第{stage_index}阶"
                }

            elif attr_type == "numeric":
                # 数值型: 默认值 + 职业加成 + 角色类型加成
                base = attr_config.get("default", 50)
                career_bonus = 0
                if career_base_attributes:
                    career_bonus = career_base_attributes.get(attr_name, 0)
                role_bonus = 10 if role_type == "protagonist" else 0

                result[attr_name] = {
                    "type": "numeric",
                    "value": base + career_bonus + role_bonus
                }

            elif attr_type == "combo_select":
                # 组合选择型: 从职业配置或默认
                default_elements = attr_config.get("default", [])
                career_elements = None
                if career_base_attributes:
                    career_elements = career_base_attributes.get(attr_name)

                elements = career_elements if career_elements else default_elements
                if isinstance(elements, str):
                    elements = [elements]

                result[attr_name] = AttributeService.calculate_combo_quality(
                    attr_config, elements
                )

        return result

    @staticmethod
    def apply_stage_growth(
        attribute_schema: Dict,
        current_attributes: Dict,
        per_stage_bonus: Dict,
        from_stage: int,
        to_stage: int
    ) -> Dict:
        """
        应用职业阶段晋升的能力增长

        Args:
            attribute_schema: 项目的属性定义
            current_attributes: 当前能力值
            per_stage_bonus: 职业的每阶段加成配置
            from_stage: 原阶段
            to_stage: 新阶段

        Returns:
            更新后的能力值字典
        """
        if isinstance(attribute_schema, str):
            attribute_schema = json.loads(attribute_schema)
        if isinstance(current_attributes, str):
            current_attributes = json.loads(current_attributes)
        if isinstance(per_stage_bonus, str):
            per_stage_bonus = json.loads(per_stage_bonus)

        result = current_attributes.copy()
        stage_diff = to_stage - from_stage

        if stage_diff <= 0:
            return result

        attributes_config = attribute_schema.get("attributes", {})

        for attr_name, bonus_config in per_stage_bonus.items():
            if attr_name not in result:
                continue

            attr_data = result[attr_name]
            if not isinstance(attr_data, dict):
                continue

            attr_type = attributes_config.get(attr_name, {}).get("type", "numeric")

            if attr_type == "numeric" and "value" in attr_data:
                # 数值型：增加固定值或百分比
                bonus_per_stage = bonus_config.get("per_stage", 0)
                if isinstance(bonus_per_stage, str) and bonus_per_stage.endswith("%"):
                    # 百分比增长
                    percent = float(bonus_per_stage.rstrip("%")) / 100
                    for _ in range(stage_diff):
                        attr_data["value"] = int(attr_data["value"] * (1 + percent))
                else:
                    # 固定值增长
                    attr_data["value"] += bonus_per_stage * stage_diff

                # 应用范围限制
                max_val = attributes_config.get(attr_name, {}).get("max", 10000)
                min_val = attributes_config.get(attr_name, {}).get("min", 0)
                attr_data["value"] = max(min_val, min(max_val, attr_data["value"]))

            elif attr_type == "stage" and "value" in attr_data:
                # 阶段型：更新阶段值和名称
                stages = attributes_config.get(attr_name, {}).get("stages", [])
                new_stage_value = to_stage
                if stages and new_stage_value <= len(stages):
                    attr_data["value"] = new_stage_value
                    attr_data["name"] = stages[new_stage_value - 1]

        return result

    @staticmethod
    def format_attributes_for_display(
        attributes: Dict,
        attribute_schema: Dict
    ) -> str:
        """
        格式化能力值为显示字符串

        Args:
            attributes: 能力值字典
            attribute_schema: 属性定义

        Returns:
            格式化的字符串
        """
        if isinstance(attributes, str):
            attributes = json.loads(attributes)
        if isinstance(attribute_schema, str):
            attribute_schema = json.loads(attribute_schema)

        display_order = attribute_schema.get("display_order", list(attributes.keys()))
        parts = []

        for attr_name in display_order:
            if attr_name not in attributes:
                continue

            attr_data = attributes[attr_name]
            if not isinstance(attr_data, dict):
                continue

            attr_type = attr_data.get("type", "numeric")

            if attr_type == "stage":
                name = attr_data.get("name", f"第{attr_data.get('value', 1)}阶")
                parts.append(f"{attr_name}: {name}")

            elif attr_type == "combo_select":
                elements = attr_data.get("elements", [])
                quality = attr_data.get("quality", "")
                elements_str = "+".join(elements) if elements else "无"
                quality_str = f" ({quality})" if quality else ""
                parts.append(f"{attr_name}: {elements_str}{quality_str}")

            elif attr_type == "numeric":
                value = attr_data.get("value", 0)
                parts.append(f"{attr_name}: {value}")

        return ", ".join(parts)

    @staticmethod
    def validate_attributes(
        attributes: Dict,
        attribute_schema: Dict
    ) -> bool:
        """
        验证能力值是否符合属性定义

        Args:
            attributes: 能力值字典
            attribute_schema: 属性定义

        Returns:
            是否有效
        """
        if isinstance(attributes, str):
            attributes = json.loads(attributes)
        if isinstance(attribute_schema, str):
            attribute_schema = json.loads(attribute_schema)

        defined_attrs = attribute_schema.get("attributes", {})

        for attr_name, attr_data in attributes.items():
            if attr_name not in defined_attrs:
                logger.warning(f"未定义的属性: {attr_name}")
                continue

            attr_config = defined_attrs[attr_name]
            attr_type = attr_config.get("type", "numeric")

            if attr_type == "numeric":
                value = attr_data.get("value", 0)
                min_val = attr_config.get("min", 0)
                max_val = attr_config.get("max", 10000)
                if not (min_val <= value <= max_val):
                    logger.warning(f"属性 {attr_name} 值 {value} 超出范围 [{min_val}, {max_val}]")
                    return False

            elif attr_type == "stage":
                value = attr_data.get("value", 1)
                stages = attr_config.get("stages", [])
                if value < 1 or value > len(stages):
                    logger.warning(f"属性 {attr_name} 阶段 {value} 无效")
                    return False

            elif attr_type == "combo_select":
                elements = attr_data.get("elements", [])
                max_select = attr_config.get("max_select", 9)  # 默认与灵根定义一致
                if len(elements) > max_select:
                    logger.warning(f"属性 {attr_name} 元素数量 {len(elements)} 超过最大值 {max_select}")
                    return False

        return True


# 创建全局服务实例
attribute_service = AttributeService()