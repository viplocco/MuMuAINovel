"""世界设定兼容性读取辅助函数"""
import json
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.project import Project


# V3 完整结构模板（用于规范化）- 通用版，支持多小说类型
V3_COMPLETE_STRUCTURE = {
    "version": 2,
    "meta": {
        "world_name": "",
        "genre_scale": "中篇",
        "creation_stage": "core"
    },
    "physical": {
        "space": {
            "world_map": None,           # 世界地图（可选）
            "key_locations": [],         # 关键地点
            "space_nodes": [],           # 新增：空间节点
            "space_channels": [],        # 新增：空间通道
            "space_features": [],        # 新增：空间特性
            "movement_rules": ""
        },
        "time": {
            "current_period": "",        # 当前时代
            "history_epochs": [],        # 新增：历史纪元
            "history_events": [],        # 新增：关键事件年表
            "time_nodes": [],            # 新增：时间节点
            "timeflow": ""               # 时间流速
        },
        "power": {
            "system_name": "",           # 力量/能力体系名称
            "levels": [],                # 等级划分
            "cultivation_method": "",    # 获取方式（通用）
            "limitations": "",
            "ability_branches": [],      # 新增：能力分支
            "power_sources": [],         # 新增：力量来源
            "level_advances": []         # 新增：等级晋升规则
        },
        "items": {
            "equipment_system": None,    # 新增：装备体系
            "consumable_system": None,   # 新增：消耗品体系
            "tool_system": None,         # 新增：工具体系
            "structure_system": None,    # 新增：结构体系
            "creature_system": None,     # 新增：生物体系
            "rare_items": [],
            "common_items": [],
            "creation_rules": ""
        }
    },
    "social": {
        "power_structure": {
            "hierarchy_rule": "",        # 等级制度
            "key_organizations": [],     # 主要组织
            "faction_classification": [],  # 新增：势力分类
            "power_fault_lines": [],       # 新增：权力断层线
            "power_balance": [],           # 新增：权力制衡
            "conflict_rules": ""
        },
        "economy": {
            "currency_system": [],       # 货币体系
            "trade_rules": "",
            "resource_distribution": "",
            "trade_networks": [],        # 新增：贸易网络
            "economic_lifelines": []     # 新增：经济命脉
        },
        "culture": {
            "values": [],                # 核心价值观
            "taboos": [],                # 禁忌
            "traditions": [],            # 传统习俗
            "language_style": "",        # 语言风格
            "core_culture": [],          # 新增：核心文化
            "religious_beliefs": [],     # 新增：宗教信仰
            "cultural_heritage": []      # 新增：文化传承
        },
        "organizations": {               # 新增：阵营组织体系
            "protagonist_factions": [],  # 主角阵营
            "antagonist_factions": [],   # 反派阵营
            "neutral_factions": [],      # 中立阵营
            "special_factions": []       # 特殊阵营
        },
        "relations": {
            "organization_relations": [],
            "inter_personal_rules": ""
        }
    },
    "metaphor": None,  # 核心阶段为 null
    "interaction": None,  # 核心阶段为 null
    "legacy": {
        "time_period": "",
        "location": "",
        "atmosphere": "",
        "rules": ""
    }
}


def normalize_world_setting_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    规范化 V3 世界设定数据，确保所有字段都存在且有正确的结构

    此函数会：
    1. 补充缺失的顶层字段
    2. 补充缺失的嵌套字段
    3. 确保数组字段是数组类型
    4. 确保字符串字段是字符串类型

    Args:
        data: 原始解析的数据（可能不完整）

    Returns:
        规范化后的完整 V3 结构
    """
    if not data:
        return V3_COMPLETE_STRUCTURE.copy()

    # 确保是字典类型
    if not isinstance(data, dict):
        return V3_COMPLETE_STRUCTURE.copy()

    result = {}

    # 顶层字段
    result["version"] = data.get("version", 2)

    # meta
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    result["meta"] = {
        "world_name": str(meta.get("world_name", "")),
        "genre_scale": str(meta.get("genre_scale", "中篇")),
        "creation_stage": str(meta.get("creation_stage", "core"))
    }

    # physical 维度
    physical = data.get("physical", {})
    if not isinstance(physical, dict):
        physical = {}

    # physical.space
    space = physical.get("space", {})
    if not isinstance(space, dict):
        space = {}
    space_locations = space.get("key_locations", [])
    if not isinstance(space_locations, list):
        space_locations = []
    # physical.time - 使用安全获取
    time_data = _safe_get_nested(physical, ["time"], {})
    if not isinstance(time_data, dict):
        time_data = {}

    # physical.power - 使用安全获取
    power_data = _safe_get_nested(physical, ["power"], {})
    if not isinstance(power_data, dict):
        power_data = {}

    # physical.items - 使用安全获取
    items_data = _safe_get_nested(physical, ["items"], {})
    if not isinstance(items_data, dict):
        items_data = {}

    result["physical"] = {
        "space": {
            "world_map": space.get("world_map"),  # 可选
            "key_locations": space_locations,
            "space_nodes": _ensure_list(space.get("space_nodes", [])),      # 新增
            "space_channels": _ensure_list(space.get("space_channels", [])), # 新增
            "space_features": _ensure_list(space.get("space_features", [])), # 新增
            "movement_rules": str(space.get("movement_rules", ""))
        },
        "time": {
            "current_period": str(time_data.get("current_period", "")),
            "history_epochs": _ensure_list(time_data.get("history_epochs", [])),   # 新增
            "history_events": _ensure_list(time_data.get("history_events", [])),   # 新增
            "time_nodes": _ensure_list(time_data.get("time_nodes", [])),           # 新增
            "timeflow": str(time_data.get("timeflow", ""))
        },
        "power": {
            "system_name": str(power_data.get("system_name", "")),
            "levels": _ensure_list(power_data.get("levels", [])),
            "cultivation_method": str(power_data.get("cultivation_method", "")),
            "limitations": str(power_data.get("limitations", "")),
            "ability_branches": _ensure_list(power_data.get("ability_branches", [])), # 新增
            "power_sources": _ensure_list(power_data.get("power_sources", [])),      # 新增
            "level_advances": _ensure_list(power_data.get("level_advances", []))     # 新增
        },
        "items": {
            "equipment_system": items_data.get("equipment_system"),      # 新增（对象）
            "consumable_system": items_data.get("consumable_system"),    # 新增
            "tool_system": items_data.get("tool_system"),                # 新增
            "structure_system": items_data.get("structure_system"),      # 新增
            "creature_system": items_data.get("creature_system"),        # 新增
            "rare_items": _ensure_list(items_data.get("rare_items", [])),
            "common_items": _ensure_list(items_data.get("common_items", [])),
            "creation_rules": str(items_data.get("creation_rules", ""))
        }
    }

    # social 维度
    social = data.get("social", {})
    if not isinstance(social, dict):
        social = {}

    power_structure = social.get("power_structure", {})
    if not isinstance(power_structure, dict):
        power_structure = {}

    culture = social.get("culture", {})
    if not isinstance(culture, dict):
        culture = {}

    # social.economy - 使用安全获取
    economy_data = _safe_get_nested(social, ["economy"], {})
    if not isinstance(economy_data, dict):
        economy_data = {}

    # social.relations - 使用安全获取
    relations_data = _safe_get_nested(social, ["relations"], {})
    if not isinstance(relations_data, dict):
        relations_data = {}

    # social.organizations - 使用安全获取（新增）
    organizations_data = _safe_get_nested(social, ["organizations"], {})
    if not isinstance(organizations_data, dict):
        organizations_data = {}

    result["social"] = {
        "power_structure": {
            "hierarchy_rule": str(power_structure.get("hierarchy_rule", "")),
            "key_organizations": _ensure_list(power_structure.get("key_organizations", [])),
            "faction_classification": _ensure_list(power_structure.get("faction_classification", [])),  # 新增
            "power_fault_lines": _ensure_list(power_structure.get("power_fault_lines", [])),            # 新增
            "power_balance": _ensure_list(power_structure.get("power_balance", [])),                    # 新增
            "conflict_rules": str(power_structure.get("conflict_rules", ""))
        },
        "culture": {
            "values": _ensure_list(culture.get("values", [])),
            "taboos": _ensure_list(culture.get("taboos", [])),
            "traditions": _ensure_list(culture.get("traditions", [])),
            "language_style": str(culture.get("language_style", "")),
            "core_culture": _ensure_list(culture.get("core_culture", [])),           # 新增
            "religious_beliefs": _ensure_list(culture.get("religious_beliefs", [])), # 新增
            "cultural_heritage": _ensure_list(culture.get("cultural_heritage", []))  # 新增
        },
        "economy": {
            "currency_system": _ensure_list(economy_data.get("currency_system", [])),
            "trade_rules": str(economy_data.get("trade_rules", "")),
            "resource_distribution": str(economy_data.get("resource_distribution", "")),
            "trade_networks": _ensure_list(economy_data.get("trade_networks", [])),      # 新增
            "economic_lifelines": _ensure_list(economy_data.get("economic_lifelines", [])) # 新增
        },
        "organizations": {
            "protagonist_factions": _ensure_list(organizations_data.get("protagonist_factions", [])),  # 新增
            "antagonist_factions": _ensure_list(organizations_data.get("antagonist_factions", [])),    # 新增
            "neutral_factions": _ensure_list(organizations_data.get("neutral_factions", [])),         # 新增
            "special_factions": _ensure_list(organizations_data.get("special_factions", []))          # 新增
        },
        "relations": {
            "organization_relations": _ensure_list(relations_data.get("organization_relations", [])),
            "inter_personal_rules": str(relations_data.get("inter_personal_rules", ""))
        }
    }

    # metaphor 维度（可选，可能为 null）
    metaphor = data.get("metaphor")
    if metaphor is not None and isinstance(metaphor, dict):
        # metaphor.themes - 安全获取
        themes_data = _safe_get_nested(metaphor, ["themes"], {})
        if not isinstance(themes_data, dict):
            themes_data = {}

        # metaphor.symbols - 安全获取
        symbols_data = _safe_get_nested(metaphor, ["symbols"], {})
        if not isinstance(symbols_data, dict):
            symbols_data = {}

        result["metaphor"] = {
            "themes": {
                "core_theme": str(themes_data.get("core_theme", "")),
                "sub_themes": _ensure_list(themes_data.get("sub_themes", [])),
                "theme_evolution": str(themes_data.get("theme_evolution", "")),
                "theme_mappings": _ensure_list(themes_data.get("theme_mappings", []))  # 新增
            },
            "symbols": {
                "visual": _ensure_list(symbols_data.get("visual", [])),
                "colors": _ensure_list(symbols_data.get("colors", [])),
                "objects": _ensure_list(symbols_data.get("objects", [])),
                "animal_symbols": _ensure_list(symbols_data.get("animal_symbols", [])),  # 新增
                "nature_symbols": _ensure_list(symbols_data.get("nature_symbols", []))   # 新增
            },
            "philosophy": _ensure_list(metaphor.get("philosophy", [])),
            "core_philosophies": _ensure_list(metaphor.get("core_philosophies", []))  # 新增
        }
    else:
        result["metaphor"] = {
            "themes": {
                "core_theme": "",
                "sub_themes": [],
                "theme_evolution": "",
                "theme_mappings": []
            },
            "symbols": {
                "visual": [],
                "colors": [],
                "objects": [],
                "animal_symbols": [],
                "nature_symbols": []
            },
            "philosophy": [],
            "core_philosophies": []
        }

    # interaction 维度（可选，可能为 null）
    interaction = data.get("interaction")
    if interaction is not None and isinstance(interaction, dict):
        # interaction.cross_rules - 安全获取
        cross_rules_data = _safe_get_nested(interaction, ["cross_rules"], {})
        if not isinstance(cross_rules_data, dict):
            cross_rules_data = {}

        # interaction.evolution - 安全获取
        evolution_data = _safe_get_nested(interaction, ["evolution"], {})
        if not isinstance(evolution_data, dict):
            evolution_data = {}

        result["interaction"] = {
            "cross_rules": {
                "physical_social": str(cross_rules_data.get("physical_social", "")),
                "social_metaphor": str(cross_rules_data.get("social_metaphor", "")),
                "metaphor_physical": str(cross_rules_data.get("metaphor_physical", ""))
            },
            "evolution": {
                "time_driven": str(evolution_data.get("time_driven", "")),
                "event_driven": str(evolution_data.get("event_driven", "")),
                "character_driven": str(evolution_data.get("character_driven", "")),
                "faction_evolution": _ensure_list(evolution_data.get("faction_evolution", [])),  # 新增
                "resource_evolution": _ensure_list(evolution_data.get("resource_evolution", [])) # 新增
            },
            "disruption_points": _ensure_list(interaction.get("disruption_points", [])),
            "disruption_consequences": _ensure_list(interaction.get("disruption_consequences", [])),  # 新增
            "repair_mechanisms": _ensure_list(interaction.get("repair_mechanisms", []))
        }
    else:
        result["interaction"] = {
            "cross_rules": {
                "physical_social": "",
                "social_metaphor": "",
                "metaphor_physical": ""
            },
            "evolution": {
                "time_driven": "",
                "event_driven": "",
                "character_driven": "",
                "faction_evolution": [],
                "resource_evolution": []
            },
            "disruption_points": [],
            "disruption_consequences": [],
            "repair_mechanisms": []
        }

    # legacy 维度
    legacy = data.get("legacy", {})
    if not isinstance(legacy, dict):
        legacy = {}
    result["legacy"] = {
        "time_period": str(legacy.get("time_period", "")),
        "location": str(legacy.get("location", "")),
        "atmosphere": str(legacy.get("atmosphere", "")),
        "rules": str(legacy.get("rules", ""))
    }

    return result


def _ensure_list(value: Any) -> list:
    """确保值是列表类型"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # 如果是单个值，转换为列表
    return [value]


def _safe_get_nested(data: Dict[str, Any], keys: list, default: Any = None) -> Any:
    """
    安全获取嵌套字典值，防止中间层级为非字典类型导致 .get() 失败

    Args:
        data: 起始字典
        keys: 键路径列表，如 ["physical", "time", "current_period"]
        default: 默认值

    Returns:
        找到的值或默认值
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def get_world_setting_for_context(project: "Project") -> Dict[str, Any]:
    """
    从项目世界设定中提取上下文信息，支持 Markdown/V2/V3 格式和 legacy 格式

    Args:
        project: 项目模型实例

    Returns:
        Dict 包含：
        - time_period: 时间背景
        - location: 地点描述
        - atmosphere: 氛围描述
        - rules: 规则描述
        - key_organizations: 主要势力列表
        - key_locations: 关键地点列表
        - power_system: 力量体系名称
    """
    # ===== 优先处理 Markdown 格式 =====
    if project.world_setting_format == "markdown" and project.world_setting_markdown:
        from app.utils.markdown_helper import (
            extract_legacy_from_markdown,
            extract_organizations_from_markdown,
            extract_locations_from_markdown,
            extract_power_levels_from_markdown,
        )

        try:
            # 提取 legacy 4字段
            legacy = extract_legacy_from_markdown(project.world_setting_markdown)

            # 提取组织/地点
            key_organizations = extract_organizations_from_markdown(project.world_setting_markdown)
            key_locations = extract_locations_from_markdown(project.world_setting_markdown)
            power_levels = extract_power_levels_from_markdown(project.world_setting_markdown)

            return {
                "time_period": legacy.get("time_period") or project.world_time_period or "未设定",
                "location": legacy.get("location") or project.world_location or "未设定",
                "atmosphere": legacy.get("atmosphere") or project.world_atmosphere or "未设定",
                "rules": legacy.get("rules") or project.world_rules or "未设定",
                "key_organizations": key_organizations,
                "key_locations": key_locations,
                "power_system": power_levels[0] if power_levels else "",
                "power_levels": power_levels,
                "world_name": "",
                "creation_stage": "markdown",
                "world_setting_markdown": project.world_setting_markdown,
            }
        except Exception as e:
            # Markdown 解析失败，降级使用 legacy 字段
            pass

    # ===== 处理 JSON 格式（V2/V3） =====
    if project.world_setting_data:
        try:
            data = json.loads(project.world_setting_data)

            # V3 格式（version=2）
            if data.get("version") == 2:
                physical = data.get("physical", {})
                social = data.get("social", {})
                legacy = data.get("legacy", {})

                # 提取关键地点
                key_locations = []
                if physical.get("space", {}).get("key_locations"):
                    key_locations = physical["space"]["key_locations"]

                # 提取主要势力
                key_organizations = []
                if social.get("power_structure", {}).get("key_organizations"):
                    key_organizations = social["power_structure"]["key_organizations"]

                # 提取力量体系
                power_system = ""
                if physical.get("power", {}).get("system_name"):
                    power_system = physical["power"]["system_name"]

                return {
                    "time_period": legacy.get("time_period", "未设定"),
                    "location": legacy.get("location", "未设定"),
                    "atmosphere": legacy.get("atmosphere", "未设定"),
                    "rules": legacy.get("rules", "未设定"),
                    "key_organizations": key_organizations,
                    "key_locations": key_locations,
                    "power_system": power_system,
                    "power_levels": physical.get("power", {}).get("levels", []),
                    "world_name": data.get("meta", {}).get("world_name", ""),
                    "creation_stage": data.get("meta", {}).get("creation_stage", "core"),
                }

            # V2 格式（version=1 或无 version）
            elif data.get("version") == 1 or data.get("core") or data.get("summary"):
                core = data.get("core", {})
                summary = data.get("summary", {})

                return {
                    "time_period": summary.get("time_period", data.get("time_period", "未设定")),
                    "location": summary.get("location", data.get("location", "未设定")),
                    "atmosphere": summary.get("atmosphere", data.get("atmosphere", "未设定")),
                    "rules": summary.get("rules", data.get("rules", "未设定")),
                    "key_organizations": core.get("key_organizations", []),
                    "key_locations": core.get("key_locations", []),
                    "power_system": core.get("power_system", ""),
                    "power_levels": [],
                    "world_name": core.get("world_name", ""),
                    "creation_stage": "v2",
                }

        except json.JSONDecodeError:
            pass
        except Exception:
            pass

    # ===== 降级：使用原有 4 字段 =====
    return {
        "time_period": project.world_time_period or "未设定",
        "location": project.world_location or "未设定",
        "atmosphere": project.world_atmosphere or "未设定",
        "rules": project.world_rules or "未设定",
        "key_organizations": [],
        "key_locations": [],
        "power_system": "",
        "power_levels": [],
        "world_name": "",
        "creation_stage": "legacy",
    }


def get_world_setting_element_names(project: "Project") -> Dict[str, list]:
    """
    仅提取世界设定中的元素名称列表，用于 AI 选择引用

    Args:
        project: 项目模型实例

    Returns:
        Dict 包含：
        - organization_names: 势力名称列表
        - location_names: 地点名称列表
        - power_levels: 力量等级名称列表
    """
    result = {
        "organization_names": [],
        "location_names": [],
        "power_levels": [],
    }

    # ===== 优先处理 Markdown 格式 =====
    if project.world_setting_format == "markdown" and project.world_setting_markdown:
        from app.utils.markdown_helper import (
            extract_organizations_from_markdown,
            extract_locations_from_markdown,
            extract_power_levels_from_markdown,
        )

        try:
            organizations = extract_organizations_from_markdown(project.world_setting_markdown)
            result["organization_names"] = [org.get("name") for org in organizations if org.get("name")]

            locations = extract_locations_from_markdown(project.world_setting_markdown)
            result["location_names"] = [loc.get("name") for loc in locations if loc.get("name")]

            result["power_levels"] = extract_power_levels_from_markdown(project.world_setting_markdown)
            return result
        except Exception:
            pass

    # ===== 处理 JSON 格式 =====
    if not project.world_setting_data:
        return result

    try:
        data = json.loads(project.world_setting_data)

        # V3 格式
        if data.get("version") == 2:
            physical = data.get("physical", {})
            social = data.get("social", {})

            # 地点名称
            locations = physical.get("space", {}).get("key_locations", [])
            result["location_names"] = [loc.get("name") for loc in locations if loc.get("name")]

            # 势力名称
            organizations = social.get("power_structure", {}).get("key_organizations", [])
            result["organization_names"] = [org.get("name") for org in organizations if org.get("name")]

            # 力量等级
            levels = physical.get("power", {}).get("levels", [])
            result["power_levels"] = levels

        # V2 格式
        elif data.get("core"):
            core = data.get("core", {})

            locations = core.get("key_locations", [])
            result["location_names"] = [loc.get("name") for loc in locations if loc.get("name")]

            organizations = core.get("key_organizations", [])
            result["organization_names"] = [org.get("name") for org in organizations if org.get("name")]

    except Exception:
        pass

    return result


def build_world_context_for_prompt(project: "Project") -> str:
    """
    构建用于 AI 提示词的世界观上下文文本

    Args:
        project: 项目模型实例

    Returns:
        格式化的世界观上下文文本
    """
    ctx = get_world_setting_for_context(project)

    parts = []
    parts.append(f"【世界观背景】")
    parts.append(f"时间背景：{ctx['time_period']}")
    parts.append(f"地点设定：{ctx['location']}")
    parts.append(f"氛围基调：{ctx['atmosphere']}")
    parts.append(f"世界规则：{ctx['rules']}")

    if ctx['key_locations']:
        parts.append(f"\n关键地点：")
        for loc in ctx['key_locations'][:5]:  # 最多5个
            parts.append(f"- {loc.get('name', '未知')}（{loc.get('type', '未知类型')}）：{loc.get('brief', '')}")

    if ctx['key_organizations']:
        parts.append(f"\n主要势力：")
        for org in ctx['key_organizations'][:5]:  # 最多5个
            parts.append(f"- {org.get('name', '未知')}（{org.get('type', '未知类型')}）：{org.get('brief', '')}")

    if ctx['power_system']:
        parts.append(f"\n力量体系：{ctx['power_system']}")

    return "\n".join(parts)