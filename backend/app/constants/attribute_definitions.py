"""能力属性定义 - 按小说类型配置不同的能力体系"""

# 灵根元素定义（9种：五行+变异）
SPIRITUAL_ROOT_ELEMENTS = {
    # 五行基础
    "金": {"name": "金", "color": "#FFD700", "traits": "锋利、穿透"},
    "木": {"name": "木", "color": "#228B22", "traits": "生机、治愈"},
    "水": {"name": "水", "color": "#1E90FF", "traits": "流动、包容"},
    "火": {"name": "火", "color": "#FF4500", "traits": "炽热、爆发"},
    "土": {"name": "土", "color": "#8B4513", "traits": "厚重、防御"},
    # 变异元素
    "风": {"name": "风", "color": "#87CEEB", "traits": "迅捷、飘逸"},
    "雷": {"name": "雷", "color": "#9370DB", "traits": "毁灭、速度"},
    "暗": {"name": "暗", "color": "#2F4F4F", "traits": "隐匿、腐蚀"},
    "光": {"name": "光", "color": "#FFFF00", "traits": "神圣、净化"},
}

# 灵根品质等级（元素数量决定品质，越少越好，修炼速度递减）
SPIRITUAL_ROOT_QUALITY = {
    1: {"name": "天灵根", "rank": "极品", "growth_rate": 3.0},
    2: {"name": "双灵根", "rank": "上品", "growth_rate": 2.0},
    3: {"name": "三灵根", "rank": "中品", "growth_rate": 1.5},
    4: {"name": "四灵根", "rank": "下品", "growth_rate": 1.2},
    5: {"name": "五灵根", "rank": "杂灵根", "growth_rate": 1.0},
    6: {"name": "六灵根", "rank": "劣灵根", "growth_rate": 0.8},
    7: {"name": "七灵根", "rank": "废灵根", "growth_rate": 0.6},
    8: {"name": "八灵根", "rank": "极废灵根", "growth_rate": 0.4},
    9: {"name": "九灵根", "rank": "零灵根", "growth_rate": 0.2},
}

# 不同小说类型的属性定义
ATTRIBUTE_DEFINITIONS_BY_GENRE = {
    "修仙": {
        "attributes": {
            "境界": {
                "type": "stage",
                "name": "境界",
                "stages": ["炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫", "仙人"],
                "default": 1,
                "growth_on_promotion": True,
            },
            "灵根": {
                "type": "combo_select",
                "name": "灵根",
                "elements": SPIRITUAL_ROOT_ELEMENTS,
                "max_select": 9,
                "quality_config": SPIRITUAL_ROOT_QUALITY,
                "default": ["水", "火"],
            },
            "灵力": {
                "type": "numeric",
                "name": "灵力",
                "min": 0,
                "max": 10000,
                "default": 100,
            },
            "悟性": {
                "type": "numeric",
                "name": "悟性",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "气运": {
                "type": "numeric",
                "name": "气运",
                "min": 0,
                "max": 100,
                "default": 50,
                "hidden": True,
            },
        },
        "display_order": ["境界", "灵根", "灵力", "悟性", "气运"],
        "primary_attribute": "境界",
    },

    "玄幻": {
        "attributes": {
            "战力等级": {
                "type": "stage",
                "name": "战力等级",
                "stages": ["凡人", "斗者", "斗师", "大斗师", "斗灵", "斗王", "斗皇", "斗宗", "斗尊", "斗圣"],
                "default": 1,
            },
            "血脉": {
                "type": "combo_select",
                "name": "血脉",
                "elements": {
                    "龙": {"name": "龙族血脉", "traits": "力量、威压"},
                    "凤": {"name": "凤族血脉", "traits": "火焰、涅槃"},
                    "虎": {"name": "虎族血脉", "traits": "凶猛、战斗"},
                    "蛇": {"name": "蛇族血脉", "traits": "阴毒、敏捷"},
                    "狼": {"name": "狼族血脉", "traits": "团结、耐力"},
                    "熊": {"name": "熊族血脉", "traits": "力量、防御"},
                    "鹰": {"name": "鹰族血脉", "traits": "视力、飞行"},
                    "龟": {"name": "龟族血脉", "traits": "长寿、防御"},
                    "麒麟": {"name": "麒麟血脉", "traits": "祥瑞、全能"},
                    "鲲鹏": {"name": "鲲鹏血脉", "traits": "吞噬、变化"},
                },
                "max_select": 3,
                "default": ["龙"],
            },
            "斗气": {
                "type": "numeric",
                "name": "斗气",
                "min": 0,
                "max": 999,
                "default": 50,
            },
            "天赋": {
                "type": "numeric",
                "name": "天赋",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["战力等级", "血脉", "斗气", "天赋"],
    },

    "仙侠": {
        "attributes": {
            "仙位": {
                "type": "stage",
                "name": "仙位",
                "stages": ["凡人", "炼气", "筑基", "金丹", "元婴", "化神", "真仙", "金仙", "大罗金仙", "混元大罗金仙"],
                "default": 1,
            },
            "灵根": {
                "type": "combo_select",
                "name": "灵根",
                "elements": SPIRITUAL_ROOT_ELEMENTS,
                "max_select": 9,
                "quality_config": SPIRITUAL_ROOT_QUALITY,
                "default": ["木"],
            },
            "法力": {
                "type": "numeric",
                "name": "法力",
                "min": 0,
                "max": 10000,
                "default": 100,
            },
            "剑意": {
                "type": "numeric",
                "name": "剑意",
                "min": 0,
                "max": 100,
                "default": 0,
                "optional": True,
            },
            "心性": {
                "type": "numeric",
                "name": "心性",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["仙位", "灵根", "法力", "心性"],
    },

    "武侠": {
        "attributes": {
            "江湖地位": {
                "type": "stage",
                "name": "江湖地位",
                "stages": ["初入江湖", "江湖小辈", "江湖名宿", "一方豪杰", "武林高手", "绝顶高手", "一代宗师", "武林盟主", "武道圣人", "传说"],
                "default": 1,
            },
            "内力": {
                "type": "numeric",
                "name": "内力",
                "min": 0,
                "max": 999,
                "default": 50,
            },
            "武功": {
                "type": "numeric",
                "name": "武功",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "身法": {
                "type": "numeric",
                "name": "身法",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["江湖地位", "内力", "武功", "身法"],
    },

    "都市": {
        "attributes": {
            "社会阶层": {
                "type": "stage",
                "name": "社会阶层",
                "stages": ["普通", "小康", "中产", "富裕", "精英", "顶层"],
                "default": 1,
            },
            "智力": {
                "type": "numeric",
                "name": "智力",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "魅力": {
                "type": "numeric",
                "name": "魅力",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "财富": {
                "type": "numeric",
                "name": "财富",
                "min": 0,
                "max": 1000,
                "default": 50,
                "unit": "万",
            },
            "社交": {
                "type": "numeric",
                "name": "社交",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["社会阶层", "智力", "魅力", "财富", "社交"],
    },

    "科幻": {
        "attributes": {
            "基因等级": {
                "type": "stage",
                "name": "基因等级",
                "stages": ["E级", "D级", "C级", "B级", "A级", "S级", "SS级", "SSS级", "X级", "神级"],
                "default": 1,
            },
            "基因序列": {
                "type": "combo_select",
                "name": "基因序列",
                "elements": {
                    "力量型": {"traits": "肌肉强化、负重提升"},
                    "速度型": {"traits": "神经反应、移动速度"},
                    "防御型": {"traits": "皮肤强化、伤害抵抗"},
                    "感知型": {"traits": "视觉强化、听觉强化"},
                    "精神型": {"traits": "脑域开发、思维加速"},
                    "能量型": {"traits": "能量操控、能量吸收"},
                    "再生型": {"traits": "伤口愈合、断肢再生"},
                    "适应型": {"traits": "环境适应、形态变化"},
                },
                "max_select": 3,
                "default": ["力量型"],
            },
            "战斗力": {
                "type": "numeric",
                "name": "战斗力",
                "min": 0,
                "max": 999999,
                "default": 1000,
            },
            "技术能力": {
                "type": "numeric",
                "name": "技术能力",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["基因等级", "基因序列", "战斗力", "技术能力"],
    },

    "奇幻": {
        "attributes": {
            "职业等级": {
                "type": "stage",
                "name": "职业等级",
                "stages": ["学徒", "初级", "中级", "高级", "大师", "宗师", "传奇", "史诗", "神话", "半神"],
                "default": 1,
            },
            "魔力": {
                "type": "numeric",
                "name": "魔力",
                "min": 0,
                "max": 10000,
                "default": 100,
            },
            "魔法元素": {
                "type": "combo_select",
                "name": "魔法亲和",
                "elements": {
                    "火": {"name": "火焰"},
                    "水": {"name": "水流"},
                    "风": {"name": "风暴"},
                    "土": {"name": "大地"},
                    "光": {"name": "光明"},
                    "暗": {"name": "暗影"},
                    "雷": {"name": "雷电"},
                    "冰": {"name": "寒冰"},
                    "自然": {"name": "自然"},
                    "时空": {"name": "时空"},
                },
                "max_select": 2,
                "default": ["火"],
            },
            "感知": {
                "type": "numeric",
                "name": "感知",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["职业等级", "魔力", "魔法元素", "感知"],
    },

    "悬疑": {
        "attributes": {
            "推理等级": {
                "type": "stage",
                "name": "推理等级",
                "stages": ["新手", "入门", "熟练", "专家", "大师", "神探"],
                "default": 1,
            },
            "推理能力": {
                "type": "numeric",
                "name": "推理能力",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "观察力": {
                "type": "numeric",
                "name": "观察力",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "心理素质": {
                "type": "numeric",
                "name": "心理素质",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "人脉": {
                "type": "numeric",
                "name": "人脉",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["推理等级", "推理能力", "观察力", "心理素质", "人脉"],
    },

    "言情": {
        "attributes": {
            "魅力": {
                "type": "numeric",
                "name": "魅力",
                "min": 0,
                "max": 100,
                "default": 70,
            },
            "情商": {
                "type": "numeric",
                "name": "情商",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "家境": {
                "type": "numeric",
                "name": "家境",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "才华": {
                "type": "numeric",
                "name": "才华",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["魅力", "情商", "家境", "才华"],
    },

    "历史": {
        "attributes": {
            "官职": {
                "type": "stage",
                "name": "官职",
                "stages": ["平民", "秀才", "举人", "进士", "翰林", "知县", "知府", "巡抚", "总督", "宰相"],
                "default": 1,
            },
            "武艺": {
                "type": "numeric",
                "name": "武艺",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "谋略": {
                "type": "numeric",
                "name": "谋略",
                "min": 0,
                "max": 100,
                "default": 50,
            },
            "声望": {
                "type": "numeric",
                "name": "声望",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        },
        "display_order": ["官职", "武艺", "谋略", "声望"],
    },
}

# 默认通用属性（当类型未匹配时使用）
DEFAULT_ATTRIBUTES = {
    "attributes": {
        "力量": {"type": "numeric", "name": "力量", "min": 0, "max": 100, "default": 50},
        "智力": {"type": "numeric", "name": "智力", "min": 0, "max": 100, "default": 50},
        "敏捷": {"type": "numeric", "name": "敏捷", "min": 0, "max": 100, "default": 50},
        "体质": {"type": "numeric", "name": "体质", "min": 0, "max": 100, "default": 50},
        "精神": {"type": "numeric", "name": "精神", "min": 0, "max": 100, "default": 50},
    },
    "display_order": ["力量", "智力", "敏捷", "体质", "精神"],
}


def get_attribute_schema_for_genre(genre: str) -> dict:
    """
    获取指定小说类型的属性定义

    Args:
        genre: 小说类型（如：修仙、玄幻、都市等）

    Returns:
        属性定义字典
    """
    return ATTRIBUTE_DEFINITIONS_BY_GENRE.get(genre, DEFAULT_ATTRIBUTES)


def get_all_genres() -> list:
    """获取所有支持的类型列表"""
    return list(ATTRIBUTE_DEFINITIONS_BY_GENRE.keys())