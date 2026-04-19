"""提示词管理服务"""
from typing import Dict, Any, Optional
import json


class WritingStyleManager:
    """写作风格管理器"""
    
    @staticmethod
    def apply_style_to_prompt(base_prompt: str, style_content: str) -> str:
        """
        将写作风格应用到基础提示词中
        
        Args:
            base_prompt: 基础提示词
            style_content: 风格要求内容
            
        Returns:
            组合后的提示词
        """
        # 在基础提示词末尾添加风格要求
        return f"{base_prompt}\n\n{style_content}\n\n请直接输出章节正文内容，不要包含章节标题和其他说明文字。"


class PromptService:
    """提示词模板管理"""
    
    # ========== V2版本提示词模板（RTCO框架）==========
    
    # 世界构建提示词 V2（RTCO框架）
    WORLD_BUILDING = """<system>
你是资深的世界观设计师，擅长为{genre}类型的小说构建真实、自洽的世界观。
</system>

<task>
【设计任务】
为小说《{title}》构建完整的世界观设定。

【核心要求】
- 主题契合：世界观必须支撑主题\"{theme}\"
- 简介匹配：为简介中的情节提供合理背景
- 类型适配：符合{genre}类型的特征
- 规模适当：根据题材选择合适的设定尺度
</task>

<input priority="P0">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
简介：{description}
</input>

<guidelines priority="P1">
【类型指导原则】

**现代都市/言情/青春**：
- 时间：当代社会（2020年代）或近未来（2030-2050年）
- 避免：大崩解、纪元、末日等宏大概念
- 重点：具体城市环境、职场文化、社会现状

**历史/古代**：
- 时间：明确的历史朝代或虚构古代
- 重点：时代特征、礼教制度、阶级分化

**玄幻/仙侠/修真**：
- 时间：修炼文明的特定时期
- 重点：修炼规则、灵气环境、门派势力

**科幻**：
- 时间：未来明确时期（如2150年、星际时代初期）
- 重点：科技水平、社会形态、文明转折

**奇幻/魔法**：
- 时间：魔法文明的特定阶段
- 重点：魔法体系、种族关系、大陆格局

**设定尺度控制**：
- 现代都市：聚焦某个城市、行业、阶层
- 校园青春：学校环境、学生生活、成长困境
- 职场言情：公司文化、行业特点、职业压力
- 史诗题材：才需要宏大的世界观架构
</guidelines>

<output priority="P0">
【输出格式】
生成包含以下四个字段的JSON对象，每个字段300-500字：

1. **time_period**（时间背景与社会状态）
   - 根据类型设定合适规模的时间背景
   - 现代题材：具体社会特征（如：2024年北京，互联网行业高速发展）
   - 历史题材：明确朝代和阶段（如：明朝嘉靖年间，海禁政策下的沿海）
   - 幻想题材：文明发展阶段，具体而非空泛
   - 阐明时代核心矛盾和社会焦虑

2. **location**（空间环境与地理特征）
   - 故事主要发生的空间环境
   - 现代题材：具体城市名或类型
   - 环境如何影响居民生存方式
   - 标志性场景描述

3. **atmosphere**（感官体验与情感基调）
   - 身临其境的感官细节（视觉、听觉、嗅觉）
   - 美学风格和色彩基调
   - 居民心理状态和情绪氛围
   - 与主题情感呼应

4. **rules**（世界规则与社会结构）
   - 世界运行的核心法则
   - 现代题材：社会规则、行业潜规则、人际法则
   - 幻想题材:力量体系、社会等级、资源分配
   - 权力结构和利益格局
   - 社会禁忌及后果

【格式规范】
- 纯JSON输出，JSON对象以左花括号开始、右花括号结束
- 无markdown标记、代码块符号
- 字段值为完整段落文本
- 不使用特殊符号包裹内容
- 提供充实原创内容

【JSON示例】
{{
  "time_period": "时间背景与社会状态的详细描述（300-500字）",
  "location": "空间环境与地理特征的详细描述（300-500字）",
  "atmosphere": "感官体验与情感基调的详细描述（300-500字）",
  "rules": "世界规则与社会结构的详细描述（300-500字）"
}}
</output>

<constraints>
【必须遵守】
✅ 简介契合：为简介情节提供合理背景
✅ 类型适配：符合{genre}的特征
✅ 主题贴合：支撑主题\"{theme}\"
✅ 具象化：用具体细节而非空洞概念
✅ 逻辑自洽：所有设定相互支撑

【禁止事项】
❌ 生成与类型不匹配的设定
❌ 为小规模题材使用宏大世界观
❌ 使用模板化、空泛的表达
❌ 输出markdown或代码块标记
</constraints>"""

    # 世界构建提示词 V2（结构化输出）
    WORLD_BUILDING_V2 = """<system>
你是资深的世界观设计师，擅长为{genre}类型的小说构建真实、自洽的世界观。
</system>

<task>
【设计任务】
为小说《{title}》构建结构化的世界观设定。

【核心要求】
- 主题契合：世界观必须支撑主题\"{theme}\"
- 简介匹配：为简介中的情节提供合理背景
- 类型适配：符合{genre}类型的特征
- 结构清晰：按指定JSON格式输出
</task>

<input priority="P0">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
简介：{description}
</input>

<guidelines priority="P1">
【类型指导原则】

**现代都市/言情/青春**：
- 重点：具体城市环境、职场文化、社会现状
- 避免使用过于宏大的时代设定

**历史/古代**：
- 重点：时代特征、礼教制度、阶级分化

**玄幻/仙侠/修真**：
- 重点：修炼规则、灵气环境、门派势力

**科幻**：
- 重点：科技水平、社会形态、文明转折

**奇幻/魔法**：
- 重点：魔法体系、种族关系、大陆格局
</guidelines>

<output priority="P0">
【输出格式】
输出纯JSON（无markdown标记），结构如下：

{{
  "version": 1,
  "core": {{
    "world_name": "世界名称（一句话，10-20字）",
    "key_locations": [
      {{ "name": "地点名称", "type": "宗门/城市/秘境/国家", "brief": "简介（20-50字）" }}
    ],
    "key_organizations": [
      {{ "name": "势力名称", "type": "宗门/商会/家族/联盟", "brief": "简介（20-50字）" }}
    ],
    "power_system": "力量体系概述（50-100字，如修炼等级、能力分类）",
    "core_rules": "核心规则（50-100字，如禁忌、法则、代价）"
  }},
  "summary": {{
    "time_period": "时间背景（300-500字，描述时代背景和社会状态）",
    "location": "地点描述（300-500字，描述主要空间环境和地理特征）",
    "atmosphere": "氛围基调（300-500字，描述感官体验和情感基调）",
    "rules": "规则描述（300-500字，描述世界运行规则和社会结构）"
  }}
}}

【约束条件】
- key_locations：最多5个元素
- key_organizations：最多5个元素
- 每个元素仅3字段：name、type、brief
- brief字段限20-50字
- 无尾随逗号，以 }} 结尾
- 所有字符串用双引号包裹
</output>

<constraints>
【必须遵守】
✅ 简介契合：为简介情节提供合理背景
✅ 类型适配：符合{genre}的特征
✅ 主题贴合：支撑主题\"{theme}\"
✅ 具象化：用具体细节而非空洞概念
✅ 逻辑自洽：所有设定相互支撑

【禁止事项】
❌ 输出markdown或代码块标记
❌ 数组超过5个元素
❌ brief字段超过50字
❌ 使用模板化、空泛的表达
❌ 尾随逗号或格式错误
</constraints>"""

    # ========== V3版本提示词模板（多维度结构）==========

    # 世界构建提示词 V3 核心阶段
    WORLD_BUILDING_V3_CORE = """<system>
你是资深的世界观设计师，擅长为{genre}类型的小说构建真实、自洽的多维度世界观。
</system>

<task>
【设计任务 - 核心阶段】
为小说《{title}》构建世界观的核心维度结构（物理维度基础 + 社会维度基础）。

【阶段说明】
这是三阶段生成流程的第一阶段（核心），后续将扩展隐喻维度和交互维度。
</task>

<input priority="P0">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
简介：{description}
章节数：{chapter_count}章
叙事视角：{narrative_perspective}
</input>

<guidelines priority="P1">
【类型指导原则】

**现代都市/言情/青春**：
- 重点：具体城市环境、职场文化、社会现状
- 时间：当代或近未来（具体年份）
- 避免：过于宏大的时代设定或极端概念

**历史/古代**：
- 重点：时代特征、礼教制度、阶级分化
- 时间：明确朝代和阶段

**玄幻/仙侠/修真**：
- 重点：修炼规则、灵气环境、门派势力
- 时间：修炼文明的特定时期

**科幻**：
- 重点：科技水平、社会形态、文明转折
- 时间：未来明确时期

**奇幻/魔法**：
- 重点：魔法体系、种族关系、大陆格局
</guidelines>

<example priority="P0">
【完整示例 - 玄幻类型】

输入：书名《灵域传说》，类型玄幻，主题"逆境崛起与守护之道"

输出：
```json
{{"version": 2,
  "meta": {{
    "world_name": "灵域大陆",
    "genre_scale": "长篇",
    "creation_stage": "core"
  }},
  "physical": {{
    "space": {{
      "key_locations": [
        {{ "name": "天玄宗", "type": "宗门", "brief": "灵域第一大宗门，传承万年，以剑道闻名于世，占据天玄山脉主峰" }},
        {{ "name": "灵雾城", "type": "城市", "brief": "位于大陆中央的商贸枢纽，灵气充沛，各国商贾云集之地" }},
        {{ "name": "幽冥深渊", "type": "秘境", "brief": "大陆最深处的禁地，传说藏有上古神器，但灵气暴乱无人敢入" }}
      ],
      "space_nodes": [
        {{ "name": "天玄山门", "type": "入口", "location": "天玄山脉南麓", "properties": ["灵气浓郁", "剑气缭绕"] }},
        {{ "name": "灵雾集市", "type": "核心区域", "location": "灵雾城中央", "properties": ["交易活跃", "情报流通"] }}
      ],
      "space_channels": [
        {{ "name": "天玄传送阵", "type": "固定通道", "source": "天玄宗", "destination": "灵雾城", "conditions": "需持有宗门令牌" }}
      ],
      "space_features": [
        {{ "name": "灵脉节点", "type": "环境特性", "effect": "灵气浓度提升，修炼速度加快", "distribution": "天玄山脉沿线" }}
      ]
    }},
    "time": {{
      "current_period": "灵气复苏后的第五纪元，修炼文明繁荣期，各大宗门争霸正酣，小型势力依附生存",
      "history_epochs": [
        {{ "name": "上古纪元", "period": "距今万年前", "impact": "灵气充沛，仙神遍地，为后世留下无数遗迹" }},
        {{ "name": "断绝纪元", "period": "距今千年前", "impact": "天地灵气骤然涌动，开启了修炼新时代" }}
      ]
    }},
    "power": {{
      "system_name": "灵气修炼体系",
      "levels": ["炼气期", "筑基期", "金丹期", "元婴期", "化神期"],
      "cultivation_method": "吸收天地灵气淬炼经脉，需配合功法心诀，天资决定修炼速度，丹药可辅助突破瓶颈",
      "limitations": "灵气浓度影响修炼效率，天资不足者难以突破筑基期",
      "ability_branches": [
        {{ "name": "剑修", "description": "以剑为媒，剑意通灵，攻击凌厉迅捷", "key_skills": ["御剑术", "剑意心法"] }},
        {{ "name": "丹修", "description": "专研丹药炼制，辅助修炼，亦可毒术伤敌", "key_skills": ["丹道心诀", "药理辨识"] }}
      ],
      "power_sources": [
        {{ "name": "天地灵气", "type": "自然来源", "acquisition": "自然环境吸收，灵脉处效率最高" }},
        {{ "name": "灵丹妙药", "type": "人工来源", "acquisition": "购买或炼制，需耗费大量资源" }}
      ]
    }},
    "items": {{
      "equipment_system": {{
        "category": "法宝",
        "tiers": ["凡品", "灵品", "仙品", "神品"],
        "crafting_rules": "需炼器师以灵火淬炼，消耗灵材，品阶取决于材料与技艺"
      }}
    }}
  }},
  "social": {{
    "power_structure": {{
      "hierarchy_rule": "宗门内部实行长老制，辈分森严：掌门至尊、长老次之、弟子依修为分级；世俗社会遵循世家垄断，平民难以翻身",
      "key_organizations": [
        {{ "name": "天玄宗", "type": "宗门", "brief": "正道领袖，剑道独尊，弟子十万，掌握灵域半数灵脉", "power_level": "高" }},
        {{ "name": "暗月盟", "type": "联盟", "brief": "魔道势力联盟，行事隐秘，擅长暗杀与诅咒之术", "power_level": "中" }},
        {{ "name": "林氏商会", "type": "商会", "brief": "灵雾城首富家族，虽无强大修士但财力雄厚，与各大宗门有合作", "power_level": "低" }}
      ],
      "power_fault_lines": [
        {{ "name": "正邪对立", "type": "理念分歧", "intensity": "高", "parties": ["天玄宗", "暗月盟"] }}
      ],
      "power_balance": [
        {{ "mechanism_name": "正邪大会", "type": "武力威慑", "participants": ["各大宗门"], "effectiveness": "每十年举行一次，避免大规模战争" }}
      ]
    }},
    "economy": {{
      "currency_system": ["灵石", "金币"],
      "resource_distribution": "灵脉集中于天玄山脉，灵材多产于幽冥深渊边缘",
      "trade_networks": [
        {{ "name": "灵雾集市", "type": "公开市场", "location": "灵雾城", "main_goods": ["灵丹", "法宝", "灵材"] }}
      ]
    }},
    "culture": {{
      "values": ["忠义为先", "师门如父", "实力至上", "诚信为本"],
      "taboos": ["背叛宗门", "泄露功法", "欺师灭祖", "私通魔道"],
      "core_culture": [
        {{ "name": "剑道文化", "type": "能力文化", "description": "剑修追求剑意通神，以剑为命，剑在人在", "practitioners": ["天玄宗弟子"] }}
      ]
    }},
    "organizations": {{
      "protagonist_factions": [
        {{ "name": "天玄宗", "type": "宗门", "brief": "主角出身宗门，正道领袖势力", "power_level": "高" }}
      ],
      "antagonist_factions": [
        {{ "name": "暗月盟", "type": "联盟", "brief": "魔道势力，主角的主要对手", "power_level": "中" }}
      ],
      "neutral_factions": [
        {{ "name": "林氏商会", "type": "商会", "brief": "中立商贸势力，与各方皆有往来", "power_level": "低" }}
      ]
    }}
  }},
  "metaphor": null,
  "interaction": null,
  "legacy": {{
    "time_period": "灵气复苏后的第五纪元，修炼文明达到鼎盛。千年前天地灵气骤然涌动，开启了修炼新时代。各大宗门在灵脉争夺中崛起，形成了今日的正邪对立格局。世俗百姓依附势力生存，弱小者只能祈求庇护。这个时代强者为尊，弱者如草芥，但也孕育着无数逆天改命的传说。",
    "location": "灵域大陆位于东方世界中央，四面环海。大陆北部是天玄山脉，绵延万里，峰峦叠嶂，灵气最盛；中部是灵雾平原，城池林立，商贸繁荣；南部是幽冥沼泽，瘴气弥漫，鲜有人迹。三大区域各具特色，构成了修炼世界的地理骨架。",
    "atmosphere": "整片大陆笼罩在灵气氤氲之中，空气中弥漫着淡淡的灵光。天玄山脉常年云雾缭绕，剑气隐现；灵雾城熙熙攘攘，各色服饰的修士穿行其间，灵器光芒闪烁；幽冥深渊阴风阵阵，时而传来诡异声响。昼夜交替间，天际常有灵气潮汐，形成绚丽的光影变幻。",
    "rules": "修炼者必须遵守宗门戒律，不得私自传授功法。灵脉归属由实力决定，弱者只能租用或依附。世俗律法在修炼界无效，强者为尊是唯一准则。正邪对立延续千年，但双方约定每十年举行一次正邪大会，以武定胜负，避免大规模战争。违反规则者将面临追杀或禁闭惩罚。"
  }}
}}```

注意示例中：
- key_locations的brief包含具体特征和重要性描述
- space_nodes展示入口和核心区域的节点结构
- ability_branches展示不同修炼分支的特点
- power_sources展示灵气和丹药两种来源
- organizations包含主角、反派、中立阵营
- legacy四个字段各300-500字，内容丰富具体
</example>

<output priority="P0">
【输出格式】
输出纯JSON（无markdown标记），结构如下：

{{
  "version": 2,
  "meta": {{
    "world_name": "世界名称（一句话，10-30字）",
    "genre_scale": "作品规模（短篇/中篇/长篇/史诗）",
    "creation_stage": "core"
  }},
  "physical": {{
    "space": {{
      "key_locations": [
        {{ "name": "地点名", "type": "城市/宗门/秘境", "brief": "简介（20-50字）" }}
      ],
      "space_nodes": [
        {{ "name": "节点名", "type": "入口/核心区域/禁区", "location": "所属区域", "properties": ["特性1", "特性2"] }}
      ],
      "space_channels": [
        {{ "name": "通道名", "type": "固定/临时/秘密", "source": "起点", "destination": "终点", "conditions": "使用条件" }}
      ]
    }},
    "time": {{
      "current_period": "当前时代（50-100字）",
      "history_epochs": [
        {{ "name": "纪元名", "period": "时间跨度", "impact": "影响描述" }}
      ]
    }},
    "power": {{
      "system_name": "力量体系名称",
      "levels": ["等级1", "等级2", "等级3"],
      "cultivation_method": "获取方式（50字）",
      "ability_branches": [
        {{ "name": "分支名", "description": "特点描述", "key_skills": ["技能1"] }}
      ],
      "power_sources": [
        {{ "name": "来源名", "type": "自然/人工/血脉", "acquisition": "获取方式" }}
      ]
    }},
    "items": {{
      "equipment_system": {{
        "category": "装备",
        "tiers": ["品阶列表"],
        "crafting_rules": "制作规则"
      }}
    }}
  }},
  "social": {{
    "power_structure": {{
      "hierarchy_rule": "等级制度（50-100字）",
      "key_organizations": [
        {{ "name": "势力名", "type": "宗门/商会/家族", "brief": "简介", "power_level": "高/中/低" }}
      ],
      "power_fault_lines": [
        {{ "name": "断层名", "type": "阶级冲突/资源争夺", "intensity": "高/中/低" }}
      ]
    }},
    "economy": {{
      "currency_system": ["货币类型"],
      "trade_networks": [
        {{ "name": "网络名", "type": "市场/拍卖/黑市", "main_goods": ["商品列表"] }}
      ]
    }},
    "culture": {{
      "values": ["核心价值观1", "核心价值观2"],
      "taboos": ["禁忌1", "禁忌2"],
      "core_culture": [
        {{ "name": "文化名", "type": "能力文化/商业文化", "description": "描述" }}
      ]
    }},
    "organizations": {{
      "protagonist_factions": [
        {{ "name": "势力名", "type": "组织类型", "brief": "简介" }}
      ],
      "antagonist_factions": [
        {{ "name": "势力名", "type": "组织类型", "brief": "简介" }}
      ]
    }}
  }},
  "metaphor": null,
  "interaction": null,
  "legacy": {{
    "time_period": "时间背景概述（300-500字）",
    "location": "地点概述（300-500字）",
    "atmosphere": "氛围概述（300-500字）",
    "rules": "规则概述（300-500字）"
  }}
}}

【约束条件】
- key_locations：最多5个元素
- space_nodes/space_channels/history_epochs：可选，各最多3个元素
- ability_branches/power_sources：可选，各最多3个元素
- power_fault_lines：可选，最多2个元素
- trade_networks：可选，最多2个元素
- protagonist_factions/antagonist_factions：各最多3个元素
- legacy四个字段各300-500字，内容丰富
- 所有字符串用双引号包裹
- 无尾随逗号，以 }} 结尾
- metaphor和interaction设为null
- 参照<example>中的丰富度输出
</output>

<constraints>
【必须遵守】
✅ 简介契合：为简介情节提供合理背景
✅ 类型适配：符合{genre}的特征
✅ 主题贴合：支撑主题\"{theme}\"
✅ 具象化：用具体细节而非空洞概念
✅ 规模适当：根据章节数选择合适尺度
✅ legacy完整：四个legacy字段各300-500字，内容丰富
✅ 参照示例：按照<example>中的格式和丰富度输出

【禁止事项】
❌ 输出markdown或代码块标记
❌ 数组超过限制数量
❌ 使用过于宏大的时代设定
❌ 模板化、空泛的表达（如"等级制度"、"简介"等纯描述词）
❌ 遗漏legacy字段
❌ hierarchy_rule为空字符串或空泛表达
❌ brief字段少于20字或过于抽象
</constraints>"""

    # 世界构建提示词 V3 扩展阶段
    WORLD_BUILDING_V3_EXTENDED = """<system>
你是资深的世界观设计师，现在需要扩展已有的核心世界观结构。
</system>

<task>
【设计任务 - 扩展阶段】
基于已生成的核心世界观，补充隐喻维度和交互维度，并完善各维度细节。

【阶段说明】
这是三阶段生成流程的第二阶段（扩展），输入是核心阶段的JSON输出。
</task>

<input priority="P0">
【已生成的核心世界观】
{core_json}

【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
</input>

<output priority="P0">
【输出格式】
输出纯JSON（无markdown标记），补充以下维度并合并到完整结构：

{{
  "version": 2,
  "meta": {{
    "world_name": "（保持核心阶段输出）",
    "genre_scale": "（保持核心阶段输出）",
    "creation_stage": "extended"
  }},
  "physical": {{
    "space": {{
      "world_map": "（可选：世界地图描述）",
      "key_locations": "（保持核心阶段输出）",
      "space_nodes": [
        {{ "name": "空间节点名称", "type": "入口/核心区域/禁区/交通枢纽", "location": "所属区域", "properties": ["特性1"], "connections": ["连接节点"] }}
      ],
      "space_channels": [
        {{ "name": "通道名称", "type": "固定/临时/秘密通道", "source": "起点", "destination": "终点", "conditions": "使用条件", "risks": "风险" }}
      ],
      "space_features": [
        {{ "name": "特性名称", "type": "环境/规则/物理特性", "effect": "影响", "distribution": "分布范围" }}
      ],
      "movement_rules": "（保持核心阶段输出）"
    }},
    "time": {{
      "current_period": "（保持核心阶段输出）",
      "history_epochs": [
        {{ "name": "纪元名称", "period": "时间跨度", "major_events": ["事件"], "impact": "影响", "legacy": "遗留" }}
      ],
      "history_events": [
        {{ "year": "年份", "event_name": "事件名称", "epoch": "所属纪元", "description": "描述", "consequence": "后果", "related_characters": ["角色"] }}
      ],
      "time_nodes": [
        {{ "name": "时间节点", "significance": "意义", "events": ["关联事件"] }}
      ],
      "timeflow": "时间流速特性"
    }},
    "power": {{
      "system_name": "（保持核心阶段输出）",
      "levels": "（保持核心阶段输出）",
      "cultivation_method": "（保持核心阶段输出）",
      "limitations": "（保持核心阶段输出）",
      "ability_branches": [
        {{ "name": "能力分支名称", "description": "描述", "key_skills": ["技能"], "advantages": ["优势"], "disadvantages": ["劣势"], "typical_practitioners": ["典型势力"] }}
      ],
      "power_sources": [
        {{ "name": "力量来源", "type": "自然/人工/血脉/社会资源", "acquisition": "获取方式", "quality_levels": ["品质等级"], "distribution": "分布" }}
      ],
      "level_advances": [
        {{ "level_name": "等级名称", "requirements": "晋升条件", "risks": "风险", "success_effects": ["成功效果"], "failure_effects": ["失败后果"] }}
      ]
    }},
    "items": {{
      "equipment_system": {{ "category": "装备", "tiers": ["等级"], "famous_items": [{{ "name": "名物", "effect": "效果", "rarity": "稀有度" }}], "crafting_rules": "制作规则" }},
      "consumable_system": {{ "category": "消耗品", "tiers": ["等级"], "famous_items": [], "crafting_rules": "" }},
      "tool_system": {{ "category": "工具", "tiers": [], "famous_items": [], "crafting_rules": "" }},
      "structure_system": {{ "category": "结构", "tiers": [], "famous_items": [], "crafting_rules": "" }},
      "creature_system": {{ "category": "生物", "tiers": [], "famous_items": [], "crafting_rules": "" }},
      "rare_items": "（保持核心阶段输出）",
      "common_items": "（补充常见物品）",
      "creation_rules": "（保持核心阶段输出）"
    }}
  }},
  "social": {{
    "power_structure": {{
      "hierarchy_rule": "（保持核心阶段输出）",
      "key_organizations": "（保持核心阶段输出）",
      "faction_classification": [
        {{ "category": "阵营类别", "characteristics": "特征", "typical_organizations": ["典型势力"], "mutual_relations": "关系" }}
      ],
      "power_fault_lines": [
        {{ "name": "断层名称", "type": "阶级冲突/资源争夺/理念分歧", "parties": ["涉及方"], "intensity": "高/中/低", "consequences": "后果" }}
      ],
      "power_balance": [
        {{ "mechanism_name": "制衡机制", "type": "联盟/法律/武力/舆论", "participants": ["参与方"], "effectiveness": "有效性" }}
      ],
      "conflict_rules": "冲突规则"
    }},
    "economy": {{
      "currency_system": "（保持核心阶段输出）",
      "resource_distribution": "（保持核心阶段输出）",
      "trade_networks": [
        {{ "name": "贸易网络", "type": "公开市场/拍卖/黑市", "location": "位置", "main_goods": ["商品"], "rules": "规则", "participants": ["参与势力"] }}
      ],
      "economic_lifelines": [
        {{ "name": "经济命脉", "type": "资源类型", "controlled_by": ["控制势力"], "importance": "重要程度", "distribution": "分布" }}
      ],
      "trade_rules": "交易规则"
    }},
    "culture": {{
      "values": "（保持核心阶段输出）",
      "taboos": "（保持核心阶段输出）",
      "traditions": "（补充传统习俗）",
      "language_style": "语言风格",
      "core_culture": [
        {{ "name": "核心文化", "type": "能力/商业/学术/宗教文化", "description": "描述", "practitioners": ["遵循者"], "significance": "意义" }}
      ],
      "religious_beliefs": [
        {{ "name": "信仰", "type": "主流/边缘/禁忌信仰", "core_beliefs": ["教义"], "practices": ["仪式"], "influence": "影响" }}
      ],
      "cultural_heritage": [
        {{ "name": "传承", "origin": "起源", "current_status": "现状", "preservation": "传承方式", "significance": "价值" }}
      ]
    }},
    "organizations": {{
      "protagonist_factions": [
        {{ "name": "势力名称", "type": "组织类型", "brief": "简介", "power_level": "等级", "specialties": ["擅长领域"], "key_members": ["核心成员"] }}
      ],
      "antagonist_factions": [],
      "neutral_factions": [],
      "special_factions": []
    }},
    "relations": {{
      "organization_relations": "（补充组织关系）",
      "inter_personal_rules": "人际规则"
    }}
  }},
  "metaphor": {{
    "symbols": {{
      "visual": ["视觉象征1", "视觉象征2"],
      "colors": ["颜色象征1"],
      "animal_symbols": [
        {{ "animal": "动物", "symbolism": "象征含义", "usage_context": "使用场景", "cultural_notes": "文化背景" }}
      ],
      "nature_symbols": [
        {{ "element": "自然元素", "symbolism": "象征含义", "manifestation": "体现", "narrative_usage": "叙事运用" }}
      ],
      "objects": ["物品象征1"]
    }},
    "themes": {{
      "core_theme": "核心主题（与{theme}呼应，50-100字）",
      "sub_themes": ["子主题1", "子主题2"],
      "theme_evolution": "主题演化路径（50字）",
      "theme_mappings": [
        {{ "mapping_type": "环境-心理/建筑-困境/等级-人生/能力-地位", "physical_manifestation": "物理体现", "metaphor_meaning": "隐喻含义", "narrative_usage": "叙事运用", "examples": ["案例"] }}
      ]
    }},
    "philosophy": {{
      "core_philosophies": [
        {{ "philosophy_name": "哲学观念", "core_concept": "核心概念", "world_manifestation": "世界观体现", "narrative_rules": ["叙事规则"], "conflicts": "冲突" }}
      ]
    }}
  }},
  "interaction": {{
    "cross_rules": {{
      "physical_social": "物理与社会交叉规则（50字）",
      "social_metaphor": "社会与隐喻交叉规则（50字）",
      "metaphor_physical": "隐喻与物理交叉规则（50字）"
    }},
    "evolution": {{
      "time_driven": "时间驱动变化（30字）",
      "event_driven": "事件驱动变化（30字）",
      "character_driven": "角色驱动变化（30字）",
      "faction_evolution": [
        {{ "faction_name": "势力", "evolution_type": "增强/衰退/分裂/合并", "trigger": "触发原因", "current_state": "当前状态", "future_trend": "趋势" }}
      ],
      "resource_evolution": [
        {{ "resource_name": "资源", "evolution_type": "增加/减少/枯竭/变异", "cause": "原因", "impact": "影响", "mitigation": "缓解措施" }}
      ]
    }},
    "disruption_points": ["可打破的规则点1", "可打破的规则点2"],
    "disruption_consequences": [
      {{ "disruption_type": "规则突破/力量失衡/秩序崩塌", "immediate_effect": "直接后果", "long_term_effect": "长期影响", "affected_dimensions": ["受影响维度"], "narrative_usage": "叙事运用" }}
    ],
    "repair_mechanisms": ["规则修复机制1"]
  }},
  "legacy": {{
    "time_period": "（保持核心阶段输出）",
    "location": "（保持核心阶段输出）",
    "atmosphere": "（保持核心阶段输出）",
    "rules": "（保持核心阶段输出）"
  }}
}}

【约束条件】
- 各数组字段最多3个元素（faction_evolution/resource_evolution/disruption_consequences最多2个）
- 保持核心阶段的physical和social核心内容不变
- creation_stage改为"extended"
</output>

<constraints>
【必须遵守】
✅ 一致性：与核心阶段输出保持一致
✅ 主题呼应：metaphor.themes与主题\"{theme}\"呼应
✅ 交叉规则：interaction.cross_rules体现各维度关联
✅ 具象化：用具体象征而非抽象概念
✅ 通用化：根据{genre}类型适配具体内容（玄幻用修炼术语，科幻用科技术语等）

【禁止事项】
❌ 修改核心阶段的meta、legacy内容
❌ 输出markdown或代码块标记
❌ 数组超过限制数量
❌ 与核心世界观矛盾的内容
❌ 使用过于特定的修仙术语（需根据小说类型调整）
</constraints>"""

    # 世界构建提示词 - Markdown格式（单阶段生成）
    WORLD_BUILDING_MARKDOWN = """<system>
你是资深的世界观设计师，擅长为各类小说构建真实、自洽、多维度的世界观。
你能根据小说类型（玄幻/科幻/都市/历史/奇幻/悬疑/武侠等）灵活调整世界观要素，使其既符合类型特征，又具有独特性。
</system>

<task>
为小说《{title}》生成完整的世界设定文档，采用Markdown格式输出。
文档需涵盖物理、社会、隐喻、交互四个维度，以及世界概述部分。
</task>

<input>
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
简介：{description}
章节数：{chapter_count}章
叙事视角：{narrative_perspective}
</input>

<guidelines>
【类型适配指导】

**玄幻/仙侠/修真**：
- 重点：修炼体系、灵气环境、门派势力、境界划分
- 空间：层级世界（比如：下界/中界/上界、天下九州、大荒万界等）、秘境、禁地
- 力量：修炼等级、功法传承、灵丹法宝
- 社会：宗门架构、正邪对立、师徒体系

**科幻**：
- 重点：科技水平、星际文明、人工智能、能源体系
- 空间：星系分区、空间站、殖民地
- 力量：科技等级、基因改造、脑机接口
- 社会：企业/政府/联盟架构、阶级分化

**奇幻/魔法**：
- 重点：魔法体系、种族关系、大陆格局
- 空间：魔法区域、元素领地、神秘遗迹
- 力量：魔法等级、元素属性、血脉传承
- 社会：王国架构、种族联盟、魔法学院

**都市/现代**：
- 重点：城市环境、职场文化、科技水平、社会现状
- 空间：城市分区、商圈、地标建筑
- 力量：技能等级、职业体系、财富地位
- 社会：公司/政府架构、阶层矛盾、行业规则

**历史/古代**：
- 重点：时代特征、礼教制度、阶级分化、战争格局
- 空间：疆域划分、城池关卡、名山大川
- 力量：武功等级、兵法传承、官职品级
- 社会：王朝架构、世家体系、科举制度

**悬疑/推理**：
- 重点：社会阴暗面、人性复杂性、隐秘组织
- 空间：城市角落、秘密场所、案发地点
- 力量：技能等级、情报网络、心理操控
- 社会：警察架构、犯罪组织、秘密势力

**武侠**：
- 重点：武功体系、江湖规矩、门派传承
- 空间：江湖地盘、名山名水、秘境遗迹
- 力量：武功等级、内功外功、兵器传承
- 社会：门派架构、正邪对立、江湖规矩
</guidelines>

<output_format>
## 输出结构（必须严格遵循）

# 世界观设定

## 基本信息
- 世界名称：一句话描述（10-30字）
- 作品规模：短篇/中篇/长篇/史诗

## 物理维度

### 空间架构
#### 世界地图
（按类型描述地理分区，如：东洲/西漠/南岭/北原/中土，或星系分区，或城市区域）

#### 空间节点
| 名称 | 类型 | 所属区域 | 特性描述 |
|------|------|----------|----------|
（列出3-5个关键节点：入口、核心区域、禁区）

#### 空间通道
| 名称 | 类型 | 起点 | 终点 | 使用条件 |
|------|------|------|------|----------|
（列出2-3个传送/通行方式）

#### 空间特性
- 重力/引力：描述特殊规则
- 环境特性：灵气/科技/魔法浓度等
- 特殊规则：某些区域的特殊限制

### 时间架构
#### 历史纪元
| 纪元名 | 时间跨度 | 主要影响 |
|--------|----------|----------|
（列出2-4个重要纪元）

#### 关键事件年表
1. **事件名**（时间）：描述
2. ...
（列出5-10个关键事件）

#### 时间流速
（描述不同区域的时间流速差异，如无差异可省略）

#### 时间节点
- 天劫日/重大节日/周期性事件等

### 力量体系
#### 力量等级
（列出等级划分，如：炼气→筑基→金丹→元婴→化神，或科技等级，或魔法等级）

#### 力量路径
| 路径名 | 特点 | 关键技能 |
|--------|------|----------|
（列出2-4条不同修炼/成长路径）

#### 力量来源
| 来源名 | 类型 | 获取方式 |
|--------|------|----------|
（列出2-3种力量/资源来源）

#### 境界突破
- 突破条件：描述
- 失败后果：描述
- 特殊机制：天劫/考验等

### 物品体系
#### 装备体系
（描述装备分级和获取规则）

#### 消耗品体系
（描述丹药/药品/补给品分类）

#### 辅助道具
（描述符箓/工具/仪器等）

#### 特殊物品
（描述宠物/坐骑/阵法系统等，如无可省略）

## 社会维度

### 权力结构
#### 等级制度
（描述地位决定因素：修为/财富/血统/职位等）

#### 组织架构
（描述宗门/公司/政府/王国的层级结构）

#### 权力断层线
| 名称 | 类型 | 涉及方 | 紧张程度 |
|------|------|--------|----------|
（列出2-3个阶层矛盾或势力冲突）

#### 权力制衡
（描述监管机制、约束规则）

### 经济体系
#### 货币体系
（列出货币类型和兑换规则）

#### 资源分布
（描述资源产地和垄断情况）

#### 贸易网络
| 名称 | 类型 | 位置 | 主要商品 |
|------|------|------|----------|
（列出2-3个市场/渠道）

#### 经济命脉
（描述关键资源控制权）

### 文化体系
#### 核心文化
（列出3-5个核心价值观或理念）

#### 宗教信仰
（描述信仰体系和主要仪式）

#### 文化禁忌
（列出3-5个禁忌及其后果）

#### 文化传承
（描述传承方式和内容）

### 组织体系
#### 主角阵营
| 名称 | 类型 | 简介 | 实力等级 |
|------|------|------|----------|
（列出主角所属或支持势力）

#### 反派阵营
| 名称 | 类型 | 简介 | 实力等级 |
|------|------|------|----------|
（列出敌对势力）

#### 中立阵营
| 名称 | 类型 | 简介 | 实力等级 |
|------|------|------|----------|
（列出第三方势力）

#### 特殊阵营
（列出隐世/神秘势力，如无可省略）

## 隐喻维度

### 符号系统
#### 视觉符号
| 符号 | 象征意义 |
|------|----------|
（列出3-5个物品/图像符号）

#### 色彩符号
| 颜色 | 含义 |
|------|------|
（列出3-5种颜色含义）

#### 动物符号
| 动物 | 象征意义 |
|------|----------|
（列出2-4种动物图腾）

#### 自然符号
| 自然元素 | 象征意义 |
|----------|----------|
（列出2-4种自然元素符号）

### 主题映射
#### 环境→心理
（描述气候/环境变化如何映射心理状态）

#### 建筑→困境
（描述建筑风格如何暗示文明困境）

#### 境界→人生
（描述力量等级如何映射人生阶段）

#### 地位→阶层
（描述权力等级如何映射社会阶层）

### 哲学内核
#### 因果逻辑
（描述因果报应机制）

#### 平衡法则
（描述阴阳/对立统一规则）

#### 自然法则
（描述顺应/逆天规则）

#### 平等理念
（描述众生/人人平等观念）

#### 基础规则
（描述五行/科技/魔法等底层规则）

## 交互维度

### 维度间交互规则
#### 物理←→社会
（描述环境与制度如何相互影响）

#### 社会←→隐喻
（描述文化与象征如何相互影响）

#### 隐喻←→物理
（描述规则与力量如何相互影响）

### 动态演化机制
#### 世界观演化
（描述随剧情推进的世界变化）

#### 势力消长
（描述组织间的兴衰规律）

#### 资源变化
（描述资源稀缺性变化）

### 破坏点与修复机制
#### 世界观漏洞
（列出可打破的规则）

#### 破坏后果
（描述打破规则的代价）

#### 修复机制
（描述弥补/恢复方法）

## 世界概述

### 时间背景
（300-500字，描述当前时代背景、历史脉络、时代特征）

### 地理环境
（300-500字，描述主要地理特征、气候环境、地貌分布）

### 氛围基调
（300-500字，描述整体氛围、情绪基调、视觉印象）

### 世界法则
（300-500字，描述核心规则、行为约束、违规后果）
</output_format>

<constraints>
【约束条件】

1. **内容充实**：
   - 每个表格至少填写指定数量的条目
   - 世界概述四个字段各300-500字，不可敷衍
   - 所有描述需具体、有画面感，避免空泛表达

2. **逻辑自洽**：
   - 各维度内容需相互呼应，形成完整世界观
   - 力量等级与组织架构需匹配
   - 经济体系与文化价值观需呼应

3. **类型契合**：
   - 内容需契合简介情节、符合类型特征
   - 玄幻类侧重修炼体系，科幻类侧重科技体系
   - 都市类贴近现实，奇幻类构建奇幻规则

4. **格式规范**：
   - 使用Markdown表格格式列出地点、势力、符号等
   - 章节标题层级清晰（##维度 → ###子维度 → ####细节）
   - 不要使用markdown代码块包裹输出内容，直接输出纯Markdown文本
</constraints>

<example>
【示例片段 - 玄幻类型】

# 世界观设定

## 基本信息
- 世界名称：灵域大陆
- 作品规模：长篇

## 物理维度

### 空间架构
#### 世界地图
- **下界·凡尘境**：东洲青岚域（30国）、西漠荒芜域（18部族）...
- **中界·修真境**：九霄云海域（浮空仙岛108座）...

#### 空间节点
| 名称 | 类型 | 所属区域 | 特性描述 |
|------|------|----------|----------|
| 天玄山门 | 入口 | 天玄山脉 | 灵气浓郁，剑气缭绕 |
| 灵雾集市 | 核心区域 | 灵雾城 | 交易活跃，情报流通 |

...

## 世界概述

### 时间背景
灵气复苏后的第五纪元，修炼文明达到鼎盛。千年前天地灵气骤然涌动，开启了修炼新时代。各大宗门在灵脉争夺中崛起，形成了今日的正邪对立格局...（300字以上）
</example>

请严格按照以上结构输出完整的Markdown文档。"""

    # 世界构建续写提示词 - Markdown格式
    WORLD_BUILDING_MARKDOWN_CONTINUE = """<system>
你正在为小说《{title}》生成世界观设定，上次因长度限制中断，请继续完成。
</system>

<context>
上次已生成内容（末尾部分）：
{previous_content_tail}

中断位置：{last_section}
缺失章节：{missing_sections}
</context>

<instruction>
从"{last_section}"之后继续生成，直接输出Markdown文本。
确保补全所有缺失章节，特别是"世界概述"四个字段（时间背景、地理环境、氛围基调、世界法则）各300-500字必须完整。
不要重复已生成的内容，直接从中断处继续。
</instruction>"""

    # 世界构建提示词 V3 完整阶段
    WORLD_BUILDING_V3_FULL = """<system>
你是资深的世界观设计师，现在需要对扩展后的世界观进行一致性校验和完善。
</system>

<task>
【设计任务 - 完整阶段】
基于核心+扩展阶段的世界观，进行一致性校验，修复潜在问题，生成最终完整结构。

【阶段说明】
这是三阶段生成流程的第三阶段（完整），输入是扩展阶段的JSON输出。
</task>

<input priority="P0">
【已生成的世界观】
{extended_json}

【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
</input>

<output priority="P0">
【输出格式】
输出纯JSON（无markdown标记），校验修复后的完整结构：

{{
  "version": 2,
  "meta": {{
    "world_name": "（保持不变）",
    "genre_scale": "（保持不变）",
    "creation_stage": "full"
  }},
  "physical": {{
    "space": "（校验并完善：key_locations与organizations地点引用一致，space_nodes覆盖主要入口）",
    "time": "（校验并完善：history_events时间线连贯，time_nodes覆盖关键转折）",
    "power": "（校验并完善：levels与level_advances对应，ability_branches覆盖主要路径）",
    "items": "（校验并完善：各system字段填充，与metaphor.symbols呼应）"
  }},
  "social": {{
    "power_structure": "（校验并完善：key_organizations与organizations字段一致，power_fault_lines覆盖主要冲突）",
    "economy": "（校验并完善：trade_networks与physical.space_nodes呼应，economic_lifelines覆盖核心资源）",
    "culture": "（校验并完善：core_culture与power.system呼应，religious_beliefs覆盖信仰体系）",
    "organizations": "（校验并完善：各阵营势力与power_structure.key_organizations引用一致）",
    "relations": "（校验并完善：organization_relations覆盖势力关系网）"
  }},
  "metaphor": {{
    "symbols": "（校验并完善：animal_symbols/nature_symbols与{genre}类型适配）",
    "themes": "（校验并完善：theme_mappings覆盖主要隐喻关系）",
    "philosophy": "（校验并完善：core_philosophies覆盖核心世界观观念）"
  }},
  "interaction": {{
    "cross_rules": "（校验并完善：覆盖所有维度交叉）",
    "evolution": "（校验并完善：faction_evolution与organizations呼应，resource_evolution与economic_lifelines呼应）",
    "disruption_points": "（校验并完善）",
    "disruption_consequences": "（校验并完善：覆盖主要破坏场景）",
    "repair_mechanisms": "（校验并完善）"
  }},
  "legacy": {{
    "time_period": "（基于完整结构重新生成300-500字概述）",
    "location": "（基于完整结构重新生成300-500字概述）",
    "atmosphere": "（基于完整结构重新生成300-500字概述）",
    "rules": "（基于完整结构重新生成300-500字概述）"
  }}
}}

【校验任务】
1. 检查physical.key_locations与social.organizations各阵营势力是否有引用冲突
2. 检查physical.space_nodes是否覆盖主要地点入口
3. 检查physical.power.ability_branches与social.culture.core_culture是否呼应
4. 检查social.economy.trade_networks与physical.space.space_channels是否呼应
5. 检查metaphor.symbols.animal_symbols/nature_symbols是否与{genre}类型适配
6. 检查interaction.evolution.faction_evolution与social.organizations是否呼应
7. 确保legacy四个字段基于完整结构重新概述（而非直接复制）

【约束条件】
- 保持原有核心内容不变
- 仅修复明显的不一致之处
- creation_stage改为"full"
- legacy字段必须重新生成概述
</output>

<constraints>
【必须遵守】
✅ 一致性校验：各维度引用无冲突
✅ 完整性：所有维度和子字段都已填充
✅ legacy概述：基于完整结构重新生成
✅ 保持核心：不修改已生成的核心内容
✅ 类型适配：确保所有字段与{genre}小说类型适配

【禁止事项】
❌ 输出markdown或代码块标记
❌ 遗漏校验步骤
❌ 直接复制扩展阶段的legacy字段
❌ 破坏已生成内容的一致性
</constraints>"""

    # 批量角色生成提示词 V2（RTCO框架）
    CHARACTERS_BATCH_GENERATION = """<system>
你是专业的角色设定师，擅长为{genre}类型的小说创建立体丰满的角色。
</system>

<task>
【生成任务】
生成{count}个角色和组织实体。

【数量要求 - 严格遵守】
数组中必须精确包含{count}个对象，不多不少。

【实体类型分配】
- 至少1个主角（protagonist）
- 多个配角（supporting）
- 可包含反派（antagonist）
- 可包含1-2个高影响力组织（power_level: 70-95）
</task>

<worldview priority="P0">
【世界观设定】
{world_setting}

主题：{theme}
类型：{genre}
</worldview>

<requirements priority="P1">
【特殊要求】
{requirements}
</requirements>

<output priority="P0">
【输出格式】
返回纯JSON数组，每个对象包含：

**角色对象**：
{{
  "name": "角色姓名",
  "age": 25,
  "gender": "男/女/其他",
  "is_organization": false,
  "role_type": "protagonist/supporting/antagonist",
  "personality": "性格特点（100-200字）：核心性格、优缺点、特殊习惯",
  "background": "背景故事（100-200字）：家庭背景、成长经历、重要转折",
  "appearance": "外貌描述（50-100字）：身高、体型、面容、着装风格",
  "traits": ["特长1", "特长2", "特长3"],
  "relationships_array": [
    {{
      "target_character_name": "已生成的角色名称",
      "relationship_type": "关系类型",
      "intimacy_level": 75,
      "description": "关系描述"
    }}
  ],
  "organization_memberships": [
    {{
      "organization_name": "已生成的组织名称",
      "position": "职位",
      "rank": 5,
      "loyalty": 80
    }}
  ]
}}

**组织对象**：
{{
  "name": "组织名称",
  "is_organization": true,
  "role_type": "supporting",
  "personality": "组织特性（100-200字）：运作方式、核心理念、行事风格",
  "background": "组织背景（100-200字）：建立历史、发展历程、重要事件",
  "appearance": "外在表现（50-100字）：总部位置、标志性建筑",
  "organization_type": "组织类型",
  "organization_purpose": "组织目的",
  "organization_members": ["成员1", "成员2"],
  "power_level": 85,
  "location": "所在地或主要活动区域",
  "motto": "组织格言、口号或宗旨",
  "color": "代表颜色",
  "traits": []
}}

【关系类型参考】
- 家族：父亲、母亲、兄弟、姐妹、子女、配偶、恋人
- 社交：师父、徒弟、朋友、同学、同事、邻居、知己
- 职业：上司、下属、合作伙伴
- 敌对：敌人、仇人、竞争对手、宿敌

【数值范围】
- intimacy_level：-100到100（负值表示敌对）
- loyalty：0到100
- rank：0到10（职位等级）
- power_level：70到95（组织影响力）
</output>

<constraints>
【必须遵守】
✅ 数量精确：数组必须包含{count}个对象
✅ 符合世界观：角色设定与世界观一致
✅ 有深度：性格和背景要立体
✅ 关系网络：角色间形成合理关系
✅ 组织合理：组织是推动剧情的关键力量

【关系约束】
✅ relationships_array只能引用本批次已出现的角色
✅ organization_memberships只能引用本批次的组织
✅ 第一个角色的relationships_array必须为空[]
✅ 禁止幻觉：不引用不存在的角色或组织

【格式约束】
✅ 纯JSON数组输出，无markdown标记
✅ 内容描述中严禁使用特殊符号（引号、方括号、书名号等）
✅ 专有名词直接书写，不使用符号包裹

【禁止事项】
❌ 生成数量不符（多于或少于{count}个）
❌ 引用不存在的角色或组织
❌ 生成低影响力的无关紧要组织
❌ 使用markdown或代码块标记
❌ 在描述中使用特殊符号
</constraints>"""

    # 大纲生成提示词 V2（RTCO框架）
    OUTLINE_CREATE = """<system>
你是经验丰富的小说作家和编剧，擅长为{genre}类型的小说设计精彩开篇。
</system>

<task>
【创作任务】
为小说《{title}》生成开篇{chapter_count}章的大纲。

【重要说明】
这是项目初始化的开头部分，不是完整大纲：
- 完成开局设定和世界观展示
- 引入主要角色，建立初始关系
- 埋下核心矛盾和悬念钩子
- 为后续剧情发展打下基础
- 不需要完整闭环，为续写留空间
</task>

<project priority="P0">
【项目信息】
书名：{title}
主题：{theme}
类型：{genre}
开篇章节数：{chapter_count}
叙事视角：{narrative_perspective}
</project>

<worldview priority="P1">
【世界观设定】
{world_setting}
</worldview>

<characters priority="P1">
【角色信息】
{characters_info}
</characters>

<mcp_context priority="P2">
{mcp_references}
</mcp_context>

<requirements priority="P1">
【其他要求】
{requirements}
</requirements>

<output priority="P0">
【输出格式】
返回包含{chapter_count}个章节对象的JSON数组：

[
  {{
   "chapter_number": 1,
   "title": "章节标题",
   "summary": "章节概要（500-1000字）：主要情节、角色互动、关键事件、冲突与转折",
   "scenes": ["场景1描述", "场景2描述", "场景3描述"],
   "characters": [
     {{"name": "角色名1", "type": "character"}},
     {{"name": "组织/势力名1", "type": "organization"}}
   ],
   "key_points": ["情节要点1", "情节要点2"],
   "emotion": "本章情感基调",
   "goal": "本章叙事目标"
 }},
 {{
   "chapter_number": 2,
   "title": "章节标题",
   "summary": "章节概要...",
   "scenes": ["场景1", "场景2"],
   "characters": [
     {{"name": "角色名2", "type": "character"}},
     {{"name": "组织名2", "type": "organization"}}
   ],
   "key_points": ["要点1", "要点2"],
   "emotion": "情感基调",
   "goal": "叙事目标"
 }}
]

【characters字段说明】
- type为"character"表示个人角色，type为"organization"表示组织/势力/门派/帮派等
- 必须区分角色和组织，不要把组织当作角色

【格式规范】
- 纯JSON数组输出，无markdown标记
- 内容描述中严禁使用特殊符号
- 专有名词直接书写
- 字段结构与已有章节完全一致
</output>

<constraints>
【开篇大纲要求】
✅ 开局设定：前几章完成世界观呈现、主角登场、初始状态
✅ 矛盾引入：引出核心冲突，但不急于展开
✅ 角色亮相：主要角色依次登场，展示性格和关系
✅ 节奏控制：开篇不宜过快，给读者适应时间
✅ 悬念设置：埋下伏笔和钩子，为续写预留空间
✅ 视角统一：采用{narrative_perspective}视角
✅ 留白艺术：结尾不收束过紧，留发展空间

【必须遵守】
✅ 数量精确：数组包含{chapter_count}个章节对象
✅ 符合类型：情节符合{genre}类型特征
✅ 主题贴合：体现主题\"{theme}\"
✅ 开篇定位：是开局而非完整故事
✅ 描述详细：每个summary 500-1000字

【禁止事项】
❌ 输出markdown或代码块标记
❌ 在描述中使用特殊符号
❌ 试图在开篇完结故事
❌ 节奏过快，信息过载
</constraints>"""
    
    # 大纲续写提示词 V2（RTCO框架 - 简化版）
    OUTLINE_CONTINUE = """<system>
你是经验丰富的小说作家和编剧，擅长续写{genre}类型的小说大纲。
</system>

<task>
【续写任务】
基于已有{current_chapter_count}章内容，续写第{start_chapter}章到第{end_chapter}章的大纲（共{chapter_count}章）。

【当前情节阶段】
{plot_stage_instruction}

【故事发展方向】
{story_direction}
</task>

<project priority="P0">
【项目信息】
书名：{title}
主题：{theme}
类型：{genre}
叙事视角：{narrative_perspective}
</project>

<worldview priority="P1">
【世界观设定】
{world_setting}
</worldview>

<previous_context priority="P0">
{recent_outlines}
</previous_context>

<characters priority="P0">
【所有角色信息】
{characters_info}
</characters>

<foreshadow_context priority="P1">
{foreshadow_reminders}
</foreshadow_context>

<memory_context priority="P2">
{memory_context}
</memory_context>

<user_input priority="P0">
【用户输入】
续写章节数：{chapter_count}章
情节阶段：{plot_stage_instruction}
故事方向：{story_direction}
其他要求：{requirements}
</user_input>

<mcp_context priority="P2">
{mcp_references}
</mcp_context>

<output priority="P0">
【输出格式】
返回第{start_chapter}到第{end_chapter}章的JSON数组（共{chapter_count}个对象）：

[
  {{
   "chapter_number": {start_chapter},
   "title": "章节标题",
   "summary": "章节概要（500-1000字）：主要情节、角色互动、关键事件、冲突与转折",
   "scenes": ["场景1描述", "场景2描述", "场景3描述"],
   "characters": [
     {{"name": "角色名1", "type": "character"}},
     {{"name": "组织/势力名1", "type": "organization"}}
   ],
   "key_points": ["情节要点1", "情节要点2"],
   "emotion": "本章情感基调",
   "goal": "本章叙事目标"
 }},
 {{
   "chapter_number": {start_chapter} + 1,
   "title": "章节标题",
   "summary": "章节概要...",
   "scenes": ["场景1", "场景2"],
   "characters": [
     {{"name": "角色名2", "type": "character"}},
     {{"name": "组织名2", "type": "organization"}}
   ],
   "key_points": ["要点1", "要点2"],
   "emotion": "情感基调",
   "goal": "叙事目标"
 }}
]

【characters字段说明】
- type为"character"表示个人角色，type为"organization"表示组织/势力/门派/帮派等
- 必须区分角色和组织，不要把组织当作角色

【格式规范】
- 纯JSON数组输出，无markdown标记
- 内容描述中严禁使用特殊符号
- 专有名词直接书写
- 字段结构与已有章节完全一致
</output>

<constraints>
【续写要求】
✅ 剧情连贯：与前文自然衔接，保持连贯性
✅ 角色发展：遵循角色成长轨迹，充分利用角色信息
✅ 情节阶段：遵循{plot_stage_instruction}的要求
✅ 风格一致：保持与已有章节相同风格和详细程度
✅ 大纲详细：充分解析最近10章大纲的structure字段信息
✅ 伏笔规划：参考已埋入伏笔，合理规划回收时机
✅ 记忆一致：确保关键情节与前文不矛盾

【必须遵守】
✅ 数量精确：数组包含{chapter_count}个章节
✅ 编号正确：从第{start_chapter}章开始
✅ 描述详细：每个summary 500-1000字
✅ 承上启下：自然衔接前文

【禁止事项】
❌ 输出markdown或代码块标记
❌ 在描述中使用特殊符号
❌ 与前文矛盾或脱节
❌ 忽略已有角色发展
❌ 忽略最近大纲中的情节线索
❌ 忽略已埋入的伏笔信息
</constraints>"""
    
    # 章节生成 - 1-N模式（第1章）
    CHAPTER_GENERATION_ONE_TO_MANY = """<system>
你是《{project_title}》的作者，一位专注于{genre}类型的网络小说家。
</system>

<task>
【创作任务】
撰写第{chapter_number}章《{chapter_title}》的完整正文。

【基本要求】
- 目标字数：{target_word_count}字（允许±200字浮动）
- 叙事视角：{narrative_perspective}
</task>

<outline priority="P0">
【本章大纲 - 必须遵循】
{chapter_outline}
</outline>

<characters priority="P1">
【本章角色 - 请严格遵循角色设定】
{characters_info}

⚠️ 角色互动须知：
- 角色之间的对话和行为必须符合其关系设定（如师徒、敌对等）
- 涉及组织的情节须体现角色在组织中的身份和职位
- 角色的能力表现须符合其职业和阶段设定
</characters>

<careers priority="P2">
【本章职业】
{chapter_careers}
</careers>

<foreshadow_reminders priority="P2">
【🎯 伏笔提醒】
{foreshadow_reminders}
</foreshadow_reminders>

<items priority="P2">
【本章相关物品 - 参考】
{chapter_items}

⚠️ 物品使用须知：
- 引用已有物品时，使用完全相同的名称（或别名）
- 描述物品效果时需符合已有设定
- 新物品出现需合理（如获得、发现、制作）
- 关键物品的流转需符合剧情逻辑
</items>

<memory priority="P2">
【相关记忆】
{relevant_memories}
</memory>

<constraints>
【必须遵守】
✅ 严格按照大纲推进情节
✅ 保持角色性格、说话方式一致
✅ 角色互动须符合关系设定（师徒、朋友、敌对等）
✅ 组织相关情节须体现成员身份和职位层级
✅ 字数控制在目标范围内
✅ 如有伏笔提醒，请在本章中适当埋入或回收相应伏笔
✅ 如有相关物品，引用时使用正确名称并遵循已有设定
✅ 世界观一致性：所有设定和能力必须符合世界观规则

【禁止事项】
❌ 输出章节标题、序号等元信息
❌ 使用"总之"、"综上所述"等AI常见总结语
❌ 在结尾处使用开放式反问
❌ 添加作者注释或创作说明
❌ 角色行为超出其职业阶段的能力范围
❌ 随意更改物品名称或违背已有物品设定
❌ 违反世界观规则（如超出能力上限、违反物理法则）
❌ 时间线混乱或地理设定冲突
</constraints>

<output>
【输出规范】
直接输出小说正文内容，从故事场景或动作开始。
无需任何前言、后记或解释性文字。

现在开始创作：
</output>"""

    # 章节生成 - 1-1模式（第1章）
    CHAPTER_GENERATION_ONE_TO_ONE = """<system>
你是《{project_title}》的作者，一位专注于{genre}类型的网络小说家。
</system>

<task priority="P0">
【创作任务】
撰写第{chapter_number}章《{chapter_title}》的完整正文。

【基本要求】
- 目标字数：{target_word_count}字（允许±200字浮动）
- 叙事视角：{narrative_perspective}
</task>

<outline priority="P0">
【本章大纲】
{chapter_outline}
</outline>

<characters priority="P1">
【本章角色】
{characters_info}
</characters>

<careers priority="P2">
【本章职业】
{chapter_careers}
</careers>

<foreshadow_reminders priority="P2">
【🎯 伏笔提醒】
{foreshadow_reminders}
</foreshadow_reminders>

<items priority="P2">
【本章相关物品 - 参考】
{chapter_items}

⚠️ 物品使用须知：
- 引用已有物品时，使用完全相同的名称（或别名）
- 描述物品效果时需符合已有设定
- 新物品出现需合理（如获得、发现、制作）
- 关键物品的流转需符合剧情逻辑
</items>

<memory priority="P2">
【相关记忆】
{relevant_memories}
</memory>

<constraints>
【必须遵守】
✅ 严格按照大纲推进情节
✅ 保持角色性格、说话方式一致
✅ 字数需要严格控制在目标字数内
✅ 如有伏笔提醒，请在本章中适当埋入或回收相应伏笔
✅ 如有相关物品，引用时使用正确名称并遵循已有设定
✅ 世界观一致性：所有设定和能力必须符合世界观规则

【禁止事项】
❌ 输出章节标题、序号等元信息
❌ 使用"总之"、"综上所述"等AI常见总结语
❌ 添加作者注释或创作说明
❌ 生成字数禁止超过目标字数
❌ 随意更改物品名称或违背已有物品设定
❌ 违反世界观规则（如超出能力上限、违反物理法则）
❌ 时间线混乱或地理设定冲突
</constraints>

<output>
【输出规范】
直接输出小说正文内容，从故事场景或动作开始。
无需任何前言、后记或解释性文字。

现在开始创作：
</output>"""

    # 章节生成 - 1-1模式（第2章及以后）
    CHAPTER_GENERATION_ONE_TO_ONE_NEXT = """<system>
你是《{project_title}》的作者，一位专注于{genre}类型的网络小说家。
</system>

<task priority="P0">
【创作任务】
撰写第{chapter_number}章《{chapter_title}》的完整正文。

【基本要求】
- 目标字数：{target_word_count}字（允许±200字浮动）
- 叙事视角：{narrative_perspective}
</task>

<outline priority="P0">
【本章大纲】
{chapter_outline}
</outline>

<previous_chapter_summary priority="P1">
【上一章剧情概要】
{previous_chapter_summary}
</previous_chapter_summary>

<previous_chapter priority="P1">
【上一章末尾500字内容】
{previous_chapter_content}
</previous_chapter>

<characters priority="P1">
【本章角色】
{characters_info}
</characters>

<careers priority="P2">
【本章职业】
{chapter_careers}
</careers>

<foreshadow_reminders priority="P2">
【🎯 伏笔提醒】
{foreshadow_reminders}
</foreshadow_reminders>

<items priority="P2">
【本章相关物品 - 参考】
{chapter_items}

⚠️ 物品使用须知：
- 引用已有物品时，使用完全相同的名称（或别名）
- 描述物品效果时需符合已有设定
- 新物品出现需合理（如获得、发现、制作）
- 关键物品的流转需符合剧情逻辑
</items>

<memory priority="P2">
【相关记忆】
{relevant_memories}
</memory>

<constraints>
【必须遵守】
✅ 严格按照大纲推进情节
✅ 自然承接上一章末尾内容，保持连贯性
✅ 保持角色性格、说话方式一致
✅ 字数需要严格控制在目标字数内
✅ 如有伏笔提醒，请在本章中适当埋入或回收相应伏笔
✅ 如有相关物品，引用时使用正确名称并遵循已有设定

【禁止事项】
❌ 输出章节标题、序号等元信息
❌ 使用"总之"、"综上所述"等AI常见总结语
❌ 在结尾处使用开放式反问
❌ 添加作者注释或创作说明
❌ 重复上一章已发生的事件
❌ 生成字数禁止超过目标字数
❌ 随意更改物品名称或违背已有物品设定
</constraints>

<output>
【输出规范】
直接输出小说正文内容，从故事场景或动作开始。
无需任何前言、后记或解释性文字。

现在开始创作：
</output>"""

    # 章节生成 - 1-N模式（第2章及以后）
    CHAPTER_GENERATION_ONE_TO_MANY_NEXT = """<system>
你是《{project_title}》的作者，一位专注于{genre}类型的网络小说家。
</system>

<task>
【创作任务】
撰写第{chapter_number}章《{chapter_title}》的完整正文。

【基本要求】
- 目标字数：{target_word_count}字（允许±200字浮动）
- 叙事视角：{narrative_perspective}
</task>

<outline priority="P0">
【本章大纲 - 必须遵循】
{chapter_outline}
</outline>

<recent_context priority="P1">
【最近章节规划 - 故事脉络参考】
{recent_chapters_context}
</recent_context>

<continuation priority="P0">
【衔接锚点 - 必须承接】
上一章结尾：
「{continuation_point}」

【🔴 上一章已完成剧情（禁止重复！）】
{previous_chapter_summary}

⚠️ 严重警告：
1. 上述"已完成剧情"和"衔接锚点"是**已经写过的**内容
2. 本章必须推进到**新的情节点**，绝对不能重新叙述已经发生的事件
3. 如果锚点是对话结束，请描写对话后的动作或场景转换，不要重复对话
4. 如果锚点是场景描写，请直接开始人物行动，不要重复描写环境
</continuation>

<characters priority="P1">
【本章角色 - 请严格遵循角色设定】
{characters_info}

⚠️ 角色互动须知：
- 角色之间的对话和行为必须符合其关系设定（如师徒、敌对等）
- 涉及组织的情节须体现角色在组织中的身份和职位
- 角色的能力表现须符合其职业和阶段设定
</characters>

<careers priority="P2">
【本章职业】
{chapter_careers}
</careers>

<foreshadow_reminders priority="P1">
【🎯 伏笔提醒 - 需关注】
{foreshadow_reminders}
</foreshadow_reminders>

<items priority="P2">
【本章相关物品 - 参考】
{chapter_items}

⚠️ 物品使用须知：
- 引用已有物品时，使用完全相同的名称（或别名）
- 描述物品效果时需符合已有设定
- 新物品出现需合理（如获得、发现、制作）
- 关键物品的流转需符合剧情逻辑
</items>

<memory priority="P2">
【相关记忆 - 参考】
{relevant_memories}
</memory>

<constraints>
【必须遵守】
✅ 严格按照大纲推进情节
✅ 自然承接上一章结尾，不重复已发生事件
✅ 保持角色性格、说话方式一致
✅ 角色互动须符合关系设定（师徒、朋友、敌对等）
✅ 组织相关情节须体现成员身份和职位层级
✅ 字数控制在目标范围内
✅ 如有伏笔提醒，请在本章中适当埋入或回收相应伏笔
✅ 如有相关物品，引用时使用正确名称并遵循已有设定
✅ 世界观一致性：所有设定和能力必须符合世界观规则

【🔴 反重复特别指令】
✅ 检查本章开篇是否与"衔接锚点"内容重复
✅ 检查本章情节是否与"上一章已完成剧情"重复
✅ 确保本章推进到了大纲中规划的新事件

【禁止事项】
❌ 输出章节标题、序号等元信息
❌ 使用"总之"、"综上所述"等AI常见总结语
❌ 在结尾处使用开放式反问
❌ 添加作者注释或创作说明
❌ 重复叙述上一章已发生的事件（包括环境描写、心理活动）
❌ 在开篇使用"接上回"、"书接上文"等套话
❌ 角色行为超出其职业阶段的能力范围
❌ 随意更改物品名称或违背已有物品设定
❌ 违反世界观规则（如超出能力上限、违反物理法则）
❌ 时间线混乱或地理设定冲突
</constraints>

<output>
【输出规范】
直接输出小说正文内容，从故事场景或动作开始。
无需任何前言、后记或解释性文字。

现在开始创作：
</output>"""

    # 单个角色生成提示词 V2（RTCO框架）
    SINGLE_CHARACTER_GENERATION = """<system>
你是专业的角色设定师，擅长创建立体饱满的小说角色。
</system>

<task>
【设计任务】
根据用户需求和项目上下文，创建一个完整的角色设定。
</task>

<context priority="P0">
【项目上下文】
{project_context}

【用户需求】
{user_input}
</context>

<output priority="P0">
【输出格式】
生成完整的角色卡片JSON对象：

{{
  "name": "角色姓名（如用户未提供则生成符合世界观的名字）",
  "age": "年龄（具体数字或年龄段）",
  "gender": "男/女/其他",
  "appearance": "外貌描述（100-150字）：身高体型、面容特征、着装风格",
  "personality": "性格特点（150-200字）：核心性格特质、优缺点、特殊习惯",
  "background": "背景故事（200-300字）：家庭背景、成长经历、重要转折、与主题关联",
  "traits": ["特长1", "特长2", "特长3"],
  "relationships_text": "人际关系的自然语言描述",
  "relationships": [
    {{
      "target_character_name": "已存在的角色名称",
      "relationship_type": "关系类型",
      "intimacy_level": 75,
      "description": "关系的详细描述",
      "started_at": "关系开始的故事时间点（可选）"
    }}
  ],
  "organization_memberships": [
    {{
      "organization_name": "已存在的组织名称",
      "position": "职位名称",
      "rank": 8,
      "loyalty": 80,
      "joined_at": "加入时间（可选）",
      "status": "active"
    }}
  ],
  "career_info": {{
    "main_career_name": "从可用主职业列表中选择的职业名称",
    "main_career_stage": 5,
    "sub_careers": [
      {{
        "career_name": "从可用副职业列表中选择的职业名称",
        "stage": 3
      }}
    ]
  }}
}}

【职业信息说明】
如果项目上下文包含职业列表：
- 主职业：从"可用主职业"列表中选择最符合角色的职业
- 主职业阶段：根据角色实力设定合理阶段（1到max_stage）
- 副职业：可选择0-2个副职业
- ⚠️ 填写职业名称而非ID，系统会自动匹配
- 职业选择必须与角色背景、能力和定位高度契合

【关系类型参考】
- 家族：父亲、母亲、兄弟、姐妹、子女、配偶、恋人
- 社交：师父、徒弟、朋友、同学、同事、邻居、知己
- 职业：上司、下属、合作伙伴
- 敌对：敌人、仇人、竞争对手、宿敌

【数值范围】
- intimacy_level：-100到100（负值表示敌对）
- loyalty：0到100
- rank：0到10
</output>

<constraints>
【必须遵守】
✅ 符合世界观：角色设定与项目世界观一致
✅ 主题关联：背景故事与项目主题关联
✅ 立体饱满：性格复杂有矛盾性，不脸谱化
✅ 为故事服务：设定要推动剧情发展
✅ 职业匹配：职业选择与角色高度契合

【角色定位要求】
✅ 主角：有成长空间和目标动机
✅ 反派：有合理动机，不脸谱化
✅ 配角：有独特性，不是工具人

【关系约束】
✅ relationships只引用已存在的角色
✅ organization_memberships只引用已存在的组织
✅ 无关系或组织时对应数组为空[]

【格式约束】
✅ 纯JSON对象输出，无markdown标记
✅ 内容描述中严禁使用特殊符号
✅ 专有名词直接书写

【禁止事项】
❌ 输出markdown或代码块标记
❌ 在描述中使用特殊符号（引号、方括号等）
❌ 引用不存在的角色或组织
❌ 脸谱化的角色设定
</constraints>"""

    # 单个组织生成提示词 V2（RTCO框架）
    SINGLE_ORGANIZATION_GENERATION = """<system>
你是专业的组织设定师，擅长创建完整的组织/势力设定。
</system>

<task>
【设计任务】
根据用户需求和项目上下文，创建一个完整的组织/势力设定。
</task>

<context priority="P0">
【项目上下文】
{project_context}

【用户需求】
{user_input}
</context>

<output priority="P0">
【输出格式】
生成完整的组织设定JSON对象：

{{
  "name": "组织名称（如用户未提供则生成符合世界观的名称）",
  "is_organization": true,
  "organization_type": "组织类型（帮派/公司/门派/学院/政府机构/宗教组织等）",
  "personality": "组织特性（150-200字）：核心理念、行事风格、文化价值观、运作方式",
  "background": "组织背景（200-300字）：建立历史、发展历程、重要事件、当前地位",
  "appearance": "外在表现（100-150字）：总部位置、标志性建筑、组织标志、制服等",
  "organization_purpose": "组织目的和宗旨：明确目标、长期愿景、行动准则",
  "power_level": 75,
  "location": "所在地点：主要活动区域、势力范围",
  "motto": "组织格言或口号",
  "traits": ["特征1", "特征2", "特征3"],
  "color": "组织代表颜色（如：深红色、金色、黑色等）",
  "organization_members": ["重要成员1", "重要成员2", "重要成员3"]
}}

【字段说明】
- power_level：0-100的整数，表示在世界中的影响力
- organization_members：组织内重要成员名字列表（可关联已有角色）
- 成立时间：在background中描述
</output>

<constraints>
【必须遵守】
✅ 符合世界观：组织设定与项目世界观一致
✅ 主题关联：背景与项目主题关联
✅ 推动剧情：组织能推动故事发展
✅ 有层级结构：内部有明确的层级和结构
✅ 势力互动：与其他势力有互动关系

【组织定位要求】
✅ 有存在必要性：不是可有可无的背景板
✅ 目标合理：不过于理想化或脸谱化
✅ 具体细节：描述详细具体，避免空泛

【格式约束】
✅ 纯JSON对象输出，无markdown标记
✅ 内容描述中严禁使用特殊符号
✅ 专有名词直接书写

【禁止事项】
❌ 输出markdown或代码块标记
❌ 在描述中使用特殊符号（引号、方括号等）
❌ 过于理想化或脸谱化的设定
❌ 空泛的描述
</constraints>"""

    # 情节分析提示词 V2（RTCO框架 + 伏笔ID追踪）
    PLOT_ANALYSIS = """<system>
你是专业的小说编辑和剧情分析师，擅长深度剖析章节内容。
</system>

<task>
【分析任务】
全面分析第{chapter_number}章《{title}》的剧情要素、钩子、伏笔、冲突和角色发展。

【🔴 伏笔追踪任务（重要）】
系统已提供【已埋入伏笔列表】，当你识别到章节中有回收伏笔时：
1. 必须从列表中找出对应的伏笔ID
2. 在 foreshadows 数组中使用 reference_foreshadow_id 字段关联
3. 如果无法确定是哪个伏笔，reference_foreshadow_id 填 null
</task>

<chapter priority="P0">
【章节信息】
章节：第{chapter_number}章
标题：{title}
字数：{word_count}字
目标字数：{target_word_count}字（用于一致性检测）

【章节内容】
{content}
</chapter>

<existing_foreshadows priority="P1">
【已埋入伏笔列表 - 用于回收匹配】
以下是本项目中已埋入但尚未回收的伏笔，分析时如发现章节内容回收了某个伏笔，请使用对应的ID：

⚠️ **超期伏笔处理规则**：
- 如果列表中的伏笔有 replan_hint 标记（超期≥5章），必须在 foreshadows 中处理：
  - 若本章回收 → type=resolved，填写 reference_foreshadow_id
  - 若剧情上已无需回收 → type=no_need_resolve，填写 reference_foreshadow_id
  - 若仍需后续回收 → 填写新的 estimated_resolve_chapter

{existing_foreshadows}
</existing_foreshadows>

<existing_items priority="P1">
【已有物品列表 - 用于物品匹配】
以下是本项目中已有的物品，分析时如发现章节涉及这些物品，请使用完全相同的名称并填写 reference_item_id：

{existing_items}
</existing_items>

<characters priority="P1">
【项目角色信息 - 用于角色状态分析】
以下是项目中已有的角色列表，分析 character_states 和 relationship_changes 时请使用这些角色的准确名称：

{characters_info}
</characters>

<character_careers priority="P2">
【角色职业等级信息 - 用于一致性检测】
以下是角色当前的职业等级状态，分析时如发现章节描述与这些状态不一致，请记录到 consistency_issues：

{character_careers}
</character_careers>

<analysis_framework priority="P0">
【分析维度】

**1. 剧情钩子 (Hooks)**
识别吸引读者的关键元素：
- 悬念钩子：未解之谜、疑问、谜团
- 情感钩子：引发共鸣的情感点
- 冲突钩子：矛盾对抗、紧张局势
- 认知钩子：颠覆认知的信息

每个钩子需要：
- 类型分类
- 具体内容描述
- 强度评分(1-10)
- 出现位置(开头/中段/结尾)
- **关键词**：【必填】从原文逐字复制8-25字的文本片段，用于精确定位

**2. 伏笔分析 (Foreshadowing) - 🔴 支持ID追踪**
- 埋下的新伏笔：内容、预期作用、隐藏程度(1-10)
- 回收的旧伏笔：【必须】从已埋入伏笔列表中匹配ID
- 伏笔质量：巧妙性和合理性
- **关键词**：【必填】从原文逐字复制8-25字

每个伏笔需要：
- **title**：简洁标题（10-20字，概括伏笔核心）
  - ⚠️ 回收伏笔时，标题应与原伏笔标题保持一致，不要添加"回收"等后缀
  - 例如：原伏笔标题是"绿头发的视觉符号"，回收时标题仍为"绿头发的视觉符号"，而非"绿头发的视觉符号回收"
- **content**：详细描述伏笔内容和预期作用
- **type**：planted（埋下）/ resolved（回收）/ no_need_resolve（无需回收）
  - planted：本章新埋下的伏笔
  - resolved：本章回收了已有伏笔（必须填写 reference_foreshadow_id）
  - no_need_resolve：超期伏笔经判断已无需回收（放弃该伏笔，必须填写 reference_foreshadow_id）
- **strength**：强度1-10（对读者的吸引力）
- **subtlety**：隐藏度1-10（越高越隐蔽）
- **reference_chapter**：回收时引用的原埋入章节号，埋下时为null
- **reference_foreshadow_id**：【回收时必填】被回收伏笔的ID（从已埋入伏笔列表中选择），埋下时为null
  - 🔴 重要：回收伏笔时，必须从【已埋入伏笔列表】中找到对应的伏笔ID并填写
  - 如果列表中有标注【ID: xxx】的伏笔，回收时必须使用该ID
  - 如果无法确定是哪个伏笔，才填写null（但应尽量避免）
- **keyword**：【必填】从原文逐字复制8-25字的定位文本
- **category**：分类（identity=身世/mystery=悬念/item=物品/relationship=关系/event=事件/ability=能力/prophecy=预言）
- **is_long_term**：是否长线伏笔（跨10章以上回收为true）
- **related_characters**：涉及的角色名列表
- **estimated_resolve_chapter**：【必填】预估回收章节号（埋下时必须预估，回收时为当前章节）

**3. 冲突分析 (Conflict)**
- 冲突类型：人与人/人与己/人与环境/人与社会
- 冲突各方及立场
- 冲突强度(1-10)
- 解决进度(0-100%)

**4. 情感曲线 (Emotional Arc)**
- 主导情绪（最多10字）
- 情感强度(1-10)
- 情绪变化轨迹

**5. 角色状态追踪 (Character Development)**
对每个出场角色分析：
- 心理状态变化(前→后)
- 关系变化
- 关键行动和决策
- 成长或退步
- **💀 存活状态（重要）**：
  - survival_status: 角色当前存活状态
  - 可选值：active(正常)/deceased(死亡)/missing(失踪)/retired(退场)
  - 默认为null（表示无变化），仅当章节中角色明确死亡、失踪或永久退场时才填写
  - 死亡/失踪需要有明确的剧情依据，不可臆测
- ** 职业变化（可选）**：
  - 仅当章节明确描述职业进展时填写
  - main_career_stage_change: 整数(+1晋升/-1退步/0无变化)
  - sub_career_changes: 副职业变化数组
  - new_careers: 新获得职业
  - career_breakthrough: 突破过程描述
- **🏛️ 组织变化（可选）**：
  - 仅当章节明确描述角色与组织关系变化时填写
  - organization_changes: 组织变动数组
  - 每项包含：organization_name(组织名)、change_type(加入joined/离开left/晋升promoted/降级demoted/开除expelled/叛变betrayed)、new_position(新职位，可选)、loyalty_change(忠诚度变化描述，可选)、description(变化描述)

**5b. 组织状态追踪 (Organization Status) - 可选**
仅当章节涉及组织势力变化时填写，分析出场组织的状态变化：
- 组织名称
- 势力等级变化(power_change: 整数，+N增强/-N削弱/0无变化)
- 据点变化(new_location: 新据点，可选)
- 宗旨/目标变化(new_purpose: 新目标，可选)
- 组织状态描述(status_description: 当前状态概述)
- 关键事件(key_event: 触发变化的事件)
- **💀 组织存续状态（重要）**：
  - is_destroyed: 组织是否被覆灭（true/false，默认false）
  - 仅当章节明确描述组织被彻底消灭、瓦解、灭亡时设为true

**5c. 物品追踪 (Item Tracking) - 可选**
仅当章节涉及物品相关内容时填写，追踪物品的出现、流转和状态变化：

**⚠️ 重要规则：分开识别多个物品**
当一句话中出现多个不同的物品时，必须将每个物品分开识别为独立的条目。
- ❌ 错误示例："三十块下品灵石和五瓶劣质聚气丹" → 物品名称："下品灵石与聚气丹"，数量：35
- ✅ 正确示例：
  - 物品名称："下品灵石"，数量：30
  - 物品名称："劣质聚气丹"，数量：5
**每个物品必须是独立的个体，即使它们同时出现或属于同一批发放。**

- **新出现物品**：首次登场的物品
  - 物品名称、类型（武器/防具/丹药/材料/法宝/其他）
  - 出现方式（获得/发现/制作等）
  - 初始归属（哪个角色获得）
- **物品流转**：物品持有权变化
  - 物品名称（必须与已有物品列表中的名称一致）
  - 从哪个角色转移到哪个角色
  - 流转方式（赠予/交易/偷窃/战利品/继承等）
- **物品状态**：物品状态变化
  - 装备/卸下
  - 消耗/销毁
  - 丢失/封印
- **数量变化**：消耗品数量变化
  - 物品名称
  - 使用/消耗数量
  - 剩余数量
- **reference_item_id**：匹配已有物品时填写（从已有物品列表中获取）

每个物品事件需要：
- **item_name**：物品名称（匹配已有物品时使用完全相同的名称）
- **item_type**：物品类型（weapon/armor/consumable/material/artifact/other）
- **event_type**：事件类型（appear/transfer/consume/destroy/equip/unequip/lose/seal/craft/find/buy/sell）
- **from_character**：原持有者（转移时必填）
- **to_character**：新持有者
- **quantity_change**：数量变化（正数增加，负数减少）
- **quantity_after**：变化后数量
- **description**：详细描述物品变化过程
- **keyword**：原文定位关键词（8-25字）
- **reference_item_id**：匹配的已有物品ID（从已有物品列表获取，新物品为null）

**⚠️ AI自动提取的物品属性（尽可能填写）**：
- **rarity**：稀有度（common/uncommon/rare/epic/legendary/artifact），根据物品描述判断
- **quality**：品质（如：上品、极品、残缺、完美等），原文提及则填写
- **special_effects**：特殊效果描述（原文提及的能力、属性加成等）
- **lore**：背景故事/来历（物品的传说、来历、历史背景）
- **value**：价值（金币数，原文提及则填写）
- **aliases**：别名/别称列表（物品的其他称呼，如"玄铁重剑"也可叫"那把剑"）
- **attributes**：属性数值对象（如：{{"攻击力": 120, "防御力": 50}}，原文有数值则提取）
- **is_plot_critical**：是否剧情关键物品（对主线剧情有重要影响的物品为true）
- **unit**：计量单位（如：个、颗、把、张、枚、瓶等，默认"个"）
- **suggested_category**：建议分类名称（从已有分类中选择最匹配的，如：法宝、丹药、武器）

**6. 关键情节点 (Plot Points)**
列出3-5个核心情节点：
- 情节内容
- 类型(revelation/conflict/resolution/transition)
- 重要性(0.0-1.0)
- 对故事的影响
- **关键词**：【必填】从原文逐字复制8-25字

**7. 场景与节奏**
- 主要场景
- 叙事节奏(快/中/慢)
- 对话与描写比例

**8. 质量评分（支持小数，严格区分度）**
评分范围：1.0-10.0，支持一位小数（如 6.5、7.8）
每个维度必须根据以下标准严格评分，避免所有内容都打中等分数：

**节奏把控 (pacing)**：
- 1.0-3.9（差）：节奏混乱，该快不快该慢不慢；场景切换生硬；大段无意义描写拖沓
- 4.0-5.9（中下）：节奏基本可读但有明显问题；部分场景过于冗长或仓促
- 6.0-7.9（中上）：节奏整体流畅，偶有小问题；张弛有度但不够精妙
- 8.0-9.4（优秀）：节奏把控精准，高潮迭起；场景切换自然，详略得当
- 9.5-10.0（完美）：节奏大师级，每个段落都恰到好处

**吸引力 (engagement)**：
- 1.0-3.9（差）：内容乏味，缺乏钩子；读者难以继续阅读
- 4.0-5.9（中下）：有基本情节但缺乏亮点；钩子设置生硬或缺失
- 6.0-7.9（中上）：有一定吸引力，钩子有效但不够巧妙
- 8.0-9.4（优秀）：引人入胜，钩子设置精妙；让人欲罢不能
- 9.5-10.0（完美）：极具吸引力，每个段落都有阅读动力

**连贯性 (coherence)**：
- 1.0-3.9（差）：逻辑混乱，前后矛盾；角色行为不合理
- 4.0-5.9（中下）：基本连贯但有明显漏洞；部分情节衔接生硬
- 6.0-7.9（中上）：整体连贯，偶有小瑕疵；角色行为基本合理
- 8.0-9.4（优秀）：逻辑严密，衔接自然；角色行为高度一致
- 9.5-10.0（完美）：无懈可击的连贯性

**整体质量 (overall)**：
- 计算公式：(pacing + engagement + coherence) / 3，保留一位小数
- 可根据综合印象±0.5调整，必须与各项分数保持一致性

**9. 改进建议（与分数关联）**
建议数量必须与整体质量分数关联：
- overall < 5.9：必须提供4-5条具体改进建议，指出严重问题
- overall 6.0-7.9：必须提供3-4条改进建议，指出主要问题
- overall 8.0-8.9：提供1-2条优化建议，指出可提升之处
- overall ≥ 9.0：提供0-1条锦上添花的建议

注：章节字数超限的建议不包括在上述数量限制内，可额外添加。

每条建议必须：
- 指出具体问题位置或类型
- 说明为什么是问题
- 给出明确的改进方向

**10. 一致性检测（Consistency Issues）- 🔴 重要**
检测章节内容与已有设定之间的矛盾，包括：

**角色状态一致性**：
- **死亡角色再现**：已死亡角色在本章出现（对比 Character.status）
- **角色位置冲突**：角色在同一时间出现在不同地点
- **能力超出设定**：角色使用了超出其职业阶段的能力（对比 CharacterCareer.current_stage）

**数量一致性**：
- **物品数量矛盾**：描述的物品数量与记录不符（对比 Item.quantity）
- **货币数量矛盾**：灵石、金币等消耗后余额描述错误
- **修为等级矛盾**：角色等级描述与记录不符（对比 CharacterCareer.current_stage）

**字数一致性**：
- **字数超标**：章节实际字数超过目标字数（对比 target_word_count）
  - 超过100%以上（如目标3000字实际6000+）：严重超标，建议大幅压缩或精简次要场景及压缩重复度高部分的描写，保留核心情节
  - 超过50%-100%（如目标3000字实际4500-6000）：中度超标，建议精简次要场景或压缩描写
  - 超过30%-50%（如目标3000字实际3900-4500）：轻微超标，建议适当压缩冗余段落
  - 超过30%以下：正常浮动，无需处理
  - 低于目标字数30%以上（如目标3000字实际2100以下）：字数不足，建议扩展细节或增加场景

**模糊数量估计规则**：
当章节中出现模糊数量描述时（如"几十个"、"数百"、"约一百"等），必须给出明确的估计值：
- "几个" → 估计 3-5，取 4
- "十几个" → 估计 12-17，取 15
- "几十个" → 估计 30-80，根据上下文取具体值（如 35、50）
- "数百" → 估计 200-800，根据上下文取具体值（如 300、500）
- "上千" → 估计 1000-3000，根据上下文取具体值
- "约X" → 直接取 X

**重要**：对于新出现的物品获取场景，如果使用模糊数量，必须在 `character_states[].item_changes[].quantity` 中填写估计的明确数量，便于后续追踪。

**伏笔一致性**：
- **伏笔遗漏**：当前章节号超过预估回收章节，但伏笔未回收
- **孤儿伏笔**：回收了从未埋入的伏笔
- **超期伏笔处理**：对于已超期多章（≥5章）的伏笔，需要在本章分析中处理：
  - 如果剧情合适，在本章回收（type=resolved）
  - 如果剧情上已不再需要回收，标注 type=no_need_resolve（无需回收）
  - 如果仍需后续回收，重新规划 estimated_resolve_chapter（更新为合理的新章节号）

每个一致性问题需要：
- **type**：问题类型（character_death/item_quantity/currency_quantity/cultivation_level/ability_overflow/foreshadow_missed/character_location/foreshadow_orphan/word_count_overflow）
- **character_name**：涉及的角色名（角色相关问题）
- **item_name**：涉及的物品名（数量相关问题）
- **issue**：具体问题描述
- **severity**：严重程度（high/medium/low）
- **suggestion**：修改建议
- **expected_value**：预期值（数量/等级类问题）
- **described_value**：章节描述的值（模糊数量保留原文描述）
- **estimated_value**：估计的明确数量（当描述值模糊时填写，便于后续追踪）
- **overflow_percent**：字数超出百分比（字数类问题）
- **reference_id**：关联的ID（如 item_id, career_id, foreshadow_id）

**11. AI味检测（AI Flavor Analysis）- 🟡 新增**
检测文本中是否存在典型AI生成痕迹，评估"AI味"程度：

**检测维度**：
- **句式单一（uniform_sentences）**：大量使用"于是"、"然后"、"接着"等程式化连接词；主谓宾结构过于统一
- **重复模式（repetitive_patterns）**：相似句式反复出现；情感描写模板化（如"心中涌起一股..."）
- **通用表达（generic_expressions）**：大量使用模糊、通用的形容词/副词（如"一股"、"某种"、"莫名"）；缺乏具体细节
- **感官缺失（lack_of_sensory_details）**：视觉、听觉、触觉、嗅觉、味觉描写稀少；过度依赖抽象描述
- **抽象堆砌（abstract_descriptions）**：过度使用"仿佛"、"宛如"、"似乎"等模糊比喻词
- **套路结构（formulaic_structure）**：开篇结尾套路化；过渡生硬；冲突解决模板化

**AI味评分方法**：
评分基于各维度检测到的问题数量和严重度综合计算：
- 每个维度检测问题数量（不限数量，有多少报多少）
- 高严重度问题权重2.0，中严重度权重1.0，低严重度权重0.5
- 计算公式参考：score = 基础分 + (问题加权总分 × 调整系数)
- **评分参考**：
  - 加权问题总数0-2：评分1.0-3.0（低AI味）
  - 加权问题总数3-5：评分4.0-6.0（中等AI味）
  - 加权问题总数6-10：评分7.0-8.5（高AI味）
  - 加权问题总数>10：评分8.6-10.0（极高AI味）

**每项AI味指标需要**：
- **type**：问题类型（uniform_sentences/repetitive_patterns/generic_expressions/lack_of_sensory_details/abstract_descriptions/formulaic_structure）
- **content**：原文中的具体示例（8-50字，必须引用原文）
- **suggestion**：具体的改进建议（如何增加细节/变化句式等）
- **severity**：严重程度（high/medium/low）
- **position_hint**：问题大致位置（开头/中段/结尾）

**AI味检测约束**：
- 必须引用原文示例，不可泛泛描述
- 建议必须具体可执行（如"将'心中涌起一股暖流'改为具体描写心跳加速、手心出汗等生理反应"）
- **不限指标数量**：检测到多少问题就列出多少，每个维度可列出多条
- **指标数量影响评分**：问题越多评分越高，而非评分决定指标数量
- **多维度覆盖**：当检测到多个维度有问题时，每个维度至少列出1条代表性示例
</analysis_framework>

<output priority="P0">
【输出格式】
返回纯JSON对象（无markdown标记）：

{{
  "hooks": [
    {{
      "type": "悬念",
      "content": "具体描述",
      "strength": 8,
      "position": "中段",
      "keyword": "从原文逐字复制的8-25字文本"
    }}
  ],
  "foreshadows": [
    {{
      "title": "伏笔简洁标题",
      "content": "伏笔详细内容和预期作用",
      "type": "planted",
      "strength": 7,
      "subtlety": 8,
      "reference_chapter": null,
      "reference_foreshadow_id": null,
      "keyword": "从原文逐字复制的8-25字文本",
      "category": "mystery",
      "is_long_term": false,
      "related_characters": ["角色A", "角色B"],
      "estimated_resolve_chapter": 15
    }},
    {{
      "title": "回收的伏笔标题",
      "content": "伏笔如何被回收的描述",
      "type": "resolved",
      "strength": 8,
      "subtlety": 6,
      "reference_chapter": 5,
      "reference_foreshadow_id": "abc123-已埋入伏笔的ID",
      "keyword": "从原文逐字复制的8-25字文本",
      "category": "mystery",
      "is_long_term": false,
      "related_characters": ["角色A"],
      "estimated_resolve_chapter": 10
    }},
    {{
      "title": "超期已久的伏笔",
      "content": "此伏笔已超期10章，经剧情分析判断已无需回收",
      "type": "no_need_resolve",
      "strength": 5,
      "subtlety": 7,
      "reference_chapter": 3,
      "reference_foreshadow_id": "xyz789-超期伏笔的ID",
      "keyword": "相关原文关键词",
      "category": "event",
      "is_long_term": false,
      "related_characters": ["角色C"],
      "estimated_resolve_chapter": null
    }}
  ],
  "conflict": {{
    "types": ["人与人", "人与己"],
    "parties": ["主角-复仇", "反派-维护现状"],
    "level": 8,
    "description": "冲突描述",
    "resolution_progress": 0.3
  }},
  "emotional_arc": {{
    "primary_emotion": "紧张焦虑",
    "intensity": 8,
    "curve": "平静→紧张→高潮→释放",
    "secondary_emotions": ["期待", "焦虑"]
  }},
  "character_states": [
    {{
      "character_name": "张三",
      "survival_status": null,
      "state_before": "犹豫",
      "state_after": "坚定",
      "psychological_change": "心理变化描述",
      "key_event": "触发事件",
      "relationship_changes": {{"李四": "关系改善"}},
      "career_changes": {{
        "main_career_stage_change": 1,
        "sub_career_changes": [{{"career_name": "炼丹", "stage_change": 1}}],
        "new_careers": [],
        "career_breakthrough": "突破描述"
      }},
      "organization_changes": [
        {{
          "organization_name": "某门派",
          "change_type": "promoted",
          "new_position": "长老",
          "loyalty_change": "忠诚度提升",
          "description": "因立下大功被提拔为长老"
        }}
      ]
    }}
  ],
  "plot_points": [
    {{
      "content": "情节点描述",
      "type": "revelation",
      "importance": 0.9,
      "impact": "推动故事发展",
      "keyword": "从原文逐字复制的8-25字文本"
    }}
  ],
  "scenes": [
    {{
      "location": "地点",
      "atmosphere": "氛围",
      "duration": "时长估计"
    }}
  ],
  "important_dialogues": [
    {{
      "speaker": "角色名",
      "content": "对话内容摘要（20-50字）",
      "context": "对话场景/背景",
      "significance": "重要性说明（对剧情/关系的影响，决定是否提取为记忆）",
      "keyword": "原文定位关键词（8-25字）"
    }}
  ],
  "organization_states": [
    {{
      "organization_name": "某门派",
      "power_change": -10,
      "new_location": null,
      "new_purpose": null,
      "status_description": "因内乱势力受损，但核心力量未动摇",
      "key_event": "长老叛变导致分支瓦解",
      "is_destroyed": false
    }}
  ],
  "items": [
    {{
      "item_name": "玄铁剑",
      "item_type": "weapon",
      "event_type": "transfer",
      "from_character": "张三",
      "to_character": "李四",
      "quantity_change": 0,
      "quantity_after": 1,
      "description": "张三将玄铁剑赠予李四作为谢礼",
      "keyword": "张三将玄铁剑赠予李四",
      "reference_item_id": null,
      "rarity": "rare",
      "quality": "上品",
      "special_effects": "附带冰属性伤害，可提升持有者三成剑气威力",
      "lore": "此剑由千年玄铁打造，曾属于一代剑圣",
      "value": 5000,
      "aliases": ["重剑", "那把黑剑"],
      "attributes": {{"攻击力": 120, "冰属性": 30}},
      "is_plot_critical": false,
      "unit": "把",
      "suggested_category": "法宝"
    }},
    {{
      "item_name": "疗伤丹",
      "item_type": "consumable",
      "event_type": "consume",
      "from_character": null,
      "to_character": null,
      "quantity_change": -3,
      "quantity_after": 7,
      "description": "李四服用了三颗疗伤丹",
      "keyword": "取出三颗疗伤丹服下",
      "reference_item_id": "已存在物品的ID",
      "rarity": "common",
      "quality": null,
      "special_effects": null,
      "lore": null,
      "value": 100,
      "aliases": ["小还丹"],
      "attributes": null,
      "is_plot_critical": false,
      "unit": "颗",
      "suggested_category": "丹药"
    }}
  ],
  "pacing": "varied",
  "dialogue_ratio": 0.4,
  "description_ratio": 0.3,
  "scores": {{
    "pacing": 6.5,
    "engagement": 5.8,
    "coherence": 7.2,
    "overall": 6.5,
    "score_justification": "节奏整体流畅但中段略显拖沓；钩子设置有效但不够巧妙；逻辑连贯无明显漏洞"
  }},
  "plot_stage": "发展",
  "suggestions": [
    "【节奏问题】第三场景的心理描写过长（约500字），建议精简至200字以内，保留核心情感即可",
    "【吸引力不足】章节中段缺乏有效钩子，建议在主角发现线索后增加一个小悬念"
  ],
  "consistency_issues": [
    {{
      "type": "item_quantity",
      "character_name": "主角",
      "item_name": "灵石",
      "expected_value": 500,
      "described_value": 1000,
      "issue": "主角持有灵石应剩余500块，但章节描述为1000块",
      "severity": "high",
      "suggestion": "修正灵石数量描述，改为'查看剩余五百块灵石'",
      "reference_id": "item_xxx"
    }},
    {{
      "type": "item_quantity",
      "character_name": "主角",
      "item_name": "金币",
      "expected_value": 300,
      "described_value": "几百枚",
      "estimated_value": 350,
      "issue": "主角花费200金币后应剩余100枚，但章节描述'钱包里有几百枚金币'，估计约350枚，数量矛盾",
      "severity": "high",
      "suggestion": "修正金币数量描述，改为'钱包里剩下一百多枚金币'",
      "reference_id": "item_yyy"
    }},
    {{
      "type": "cultivation_level",
      "character_name": "李四",
      "career_name": "剑修",
      "expected_value": 3,
      "described_value": 5,
      "issue": "李四当前应为剑道第3阶段，但章节描述为第5阶段",
      "severity": "high",
      "suggestion": "修正等级描述，或添加突破情节",
      "reference_id": "career_xxx"
    }},
    {{
      "type": "word_count_overflow",
      "expected_value": 3000,
      "described_value": 6500,
      "overflow_percent": 117,
      "issue": "章节目标字数为3000字，实际字数6500字，超出117%，属于严重超标",
      "severity": "high",
      "suggestion": "建议大幅压缩或精简次要场景及压缩重复度高部分的描写，保留核心情节"
    }},
    {{
      "type": "word_count_overflow",
      "expected_value": 3000,
      "described_value": 4800,
      "overflow_percent": 60,
      "issue": "章节目标字数为3000字，实际字数4800字，超出60%，属于中度超标",
      "severity": "medium",
      "suggestion": "建议精简次要场景描写和对话，适当压缩心理描写段落"
    }}
  ],
  "ai_flavor": {{
    "score": 5.8,
    "score_justification": "检测到6个问题：2个高严重度(句式重复、抽象描写)+3个中严重度+1个低严重度，加权总分=(2×2+3×1+1×0.5)=7.5，对应评分区间4-6",
    "indicators": [
      {{
        "type": "repetitive_patterns",
        "content": "于是她转身离开，然后眼泪流了下来，接着...",
        "suggestion": "变换连接词，使用动作衔接情感：'她沉默着走向门口，眼泪已在眼眶打转，脚步却没停'",
        "severity": "medium",
        "position_hint": "中段"
      }},
      {{
        "type": "generic_expressions",
        "content": "心中涌起一股难以名状的情绪",
        "suggestion": "将抽象情绪转为具体描写：心跳加速、呼吸急促、手心出汗等生理反应",
        "severity": "high",
        "position_hint": "结尾"
      }},
      {{
        "type": "lack_of_sensory_details",
        "content": "房间里很安静，气氛有些压抑",
        "suggestion": "增加感官细节：昏暗的光线、尘埃在空中漂浮、墙上的旧照片、门轴的吱呀声",
        "severity": "medium",
        "position_hint": "开头"
      }},
      {{
        "type": "uniform_sentences",
        "content": "他站起身来，走到窗前，看着外面的天空",
        "suggestion": "变化句式结构：'窗外是一片灰蒙蒙的天空，他不由自主地站起身，缓步走向窗边'",
        "severity": "low",
        "position_hint": "中段"
      }},
      {{
        "type": "abstract_descriptions",
        "content": "仿佛整个世界都在这一刻静止了",
        "suggestion": "具体化描写：'周围的一切仿佛被按下了暂停键——谈话声戛然而止，行人的脚步停住，就连飘落的树叶也悬在半空'",
        "severity": "high",
        "position_hint": "结尾"
      }},
      {{
        "type": "formulaic_structure",
        "content": "就这样，一切都结束了",
        "suggestion": "避免套路结尾：改用具体场景收尾，如描写一个细节画面或角色的具体动作",
        "severity": "medium",
        "position_hint": "结尾"
      }}
    ],
    "overall_report": "本章节AI味评分为5.8分，属于中等水平。共检测到6个问题点，涉及4个检测维度。主要问题集中在句式重复和抽象描写上，建议增加具体的感官细节和变换句式连接词，以降低AI感并增加个人风格。"
  }}
}}
</output>

<constraints>
【必须遵守】
✅ keyword字段必填：钩子、伏笔、情节点的keyword不能为空
✅ 逐字复制：keyword必须从原文复制，长度8-25字
✅ 精确定位：keyword能在原文中精确找到
✅ 职业变化可选：仅当章节明确描述时填写
✅ 组织变化可选：仅当章节明确描述角色与组织关系变动时填写（character_states中的organization_changes）
✅ 组织状态可选：仅当章节明确描述组织势力/据点/目标变化时填写（organization_states顶级字段）
✅ 存活状态谨慎：survival_status仅当章节有明确死亡/失踪/退场描写时填写，默认null
✅ 组织覆灭谨慎：is_destroyed仅当组织被彻底消灭时设true，组织受损不算覆灭
✅ 【伏笔ID追踪】回收伏笔时，必须从【已埋入伏笔列表】中查找匹配的ID填入 reference_foreshadow_id
✅ 【物品追踪】匹配已有物品时，item_name必须与已有物品列表中的名称完全一致，并填写 reference_item_id
✅ 【物品可选】items数组可选，仅当章节涉及物品时填写

【评分约束 - 严格执行】
✅ 严格按评分标准打分，支持小数（如6.5、7.2、8.3）
✅ 不要默认给7.0-8.0分，差的内容必须给低分（1.0-5.0），好的内容才给高分（8.0-10.0）
✅ score_justification必填：简要说明各项评分的依据
✅ 建议数量必须与overall分数关联：
   - overall≤4.0 → 4-5条建议
   - overall 4.0-6.0 → 3-4条建议
   - overall 6.0-8.0 → 1-2条建议
   - overall≥8.0 → 0-1条建议
✅ 每条建议必须标注问题类型（如【节奏问题】【描写不足】等）

【一致性检测约束】
✅ 对比角色职业等级信息中的 current_stage，如章节描述等级不符，记录到 consistency_issues
✅ 对比已有物品列表中的 quantity，如章节描述数量不符，记录到 consistency_issues
✅ 对比角色存活状态（Character.status），如死亡角色出现，记录到 consistency_issues
✅ consistency_issues 数组可选：仅当发现实际矛盾时填写，无问题则为空数组 []

【禁止事项】
❌ keyword使用概括或改写的文字
❌ 输出markdown标记
❌ 遗漏必填的keyword字段
❌ 无根据地添加职业变化
❌ 无根据地添加组织变化或组织状态变化
❌ 无确切剧情依据地标记角色死亡或组织覆灭
❌ 所有章节都打7-8分的"安全分"
❌ 高分章节给大量建议，或低分章节不给建议
</constraints>"""

    # 大纲单批次展开提示词 V2（RTCO框架）
    OUTLINE_EXPAND_SINGLE = """<system>
你是专业的小说情节架构师，擅长将大纲节点展开为详细章节规划。
</system>

<task>
【展开任务】
将第{outline_order_index}节大纲《{outline_title}》展开为{target_chapter_count}个章节的详细规划。

【展开策略】
{strategy_instruction}
</task>

<project priority="P1">
【项目信息】
小说名称：{project_title}
类型：{project_genre}
主题：{project_theme}
叙事视角：{project_narrative_perspective}

【世界观设定】
{project_world_setting}
</project>

<characters priority="P1">
【角色信息】
{characters_info}
</characters>

<outline_node priority="P0">
【当前大纲节点 - 展开对象】
序号：第 {outline_order_index} 节
标题：{outline_title}
内容：{outline_content}
</outline_node>

<context priority="P2">
【上下文参考】
{context_info}
</context>

<output priority="P0">
【输出格式】
返回{target_chapter_count}个章节规划的JSON数组：

[
  {{
    "sub_index": 1,
    "title": "章节标题（体现核心冲突或情感）",
    "plot_summary": "剧情摘要（200-300字）：详细描述该章发生的事件，仅限当前大纲内容",
    "key_events": ["关键事件1", "关键事件2", "关键事件3"],
    "character_focus": ["角色A", "角色B"],
    "emotional_tone": "情感基调（如：紧张、温馨、悲伤）",
    "narrative_goal": "叙事目标（该章要达成的叙事效果）",
    "conflict_type": "冲突类型（如：内心挣扎、人际冲突）",
    "estimated_words": 3000{scene_field}
  }}
]

【格式规范】
- 纯JSON数组输出，无其他文字
- 内容描述中严禁使用特殊符号
</output>

<constraints>
【⚠️ 内容边界约束 - 必须严格遵守】
✅ 只能展开当前大纲节点的内容
✅ 深化当前大纲，而非跨越到后续
✅ 放慢叙事节奏，充分体验当前阶段

❌ 绝对不能推进到后续大纲内容
❌ 不要让剧情快速推进
❌ 不要提前展开【后一节】的内容

【展开原则】
✅ 将单一事件拆解为多个细节丰富的章节
✅ 深入挖掘情感、心理、环境、对话
✅ 每章是当前大纲内容的不同侧面或阶段

【🔴 相邻章节差异化约束（防止重复）】
✅ 每章有独特的开场方式（不同场景、时间点、角色状态）
✅ 每章有独特的结束方式（不同悬念、转折、情感收尾）
✅ key_events在相邻章节间绝不重叠
✅ plot_summary描述该章独特内容，不与其他章雷同
✅ 同一事件的不同阶段要明确区分"前、中、后"

【章节间要求】
✅ 衔接自然流畅（每章从不同起点开始）
✅ 剧情递进合理（但不超出当前大纲边界）
✅ 节奏张弛有度
✅ 每章有明确且独特的叙事价值
✅ 最后一章结束时恰好完成当前大纲内容
✅ 关键事件无重叠：检查相邻章节key_events

【禁止事项】
❌ 输出非JSON格式
❌ 剧情越界到后续大纲
❌ 相邻章节内容重复
❌ 关键事件雷同
</constraints>"""

    # 大纲分批展开提示词 V2（RTCO框架）
    OUTLINE_EXPAND_MULTI = """<system>
你是专业的小说情节架构师，擅长分批展开大纲节点。
</system>

<task>
【展开任务】
继续展开第{outline_order_index}节大纲《{outline_title}》，生成第{start_index}-{end_index}节（共{target_chapter_count}个章节）的详细规划。

【分批说明】
- 这是整个展开的一部分
- 必须与前面已生成的章节自然衔接
- 从第{start_index}节开始编号
- 继续深化当前大纲内容

【展开策略】
{strategy_instruction}
</task>

<project priority="P1">
【项目信息】
小说名称：{project_title}
类型：{project_genre}
主题：{project_theme}
叙事视角：{project_narrative_perspective}

【世界观设定】
{project_world_setting}
</project>

<characters priority="P1">
【角色信息】
{characters_info}
</characters>

<outline_node priority="P0">
【当前大纲节点 - 展开对象】
序号：第 {outline_order_index} 节
标题：{outline_title}
内容：{outline_content}
</outline_node>

<context priority="P2">
【上下文参考】
{context_info}

【已生成的前序章节】
{previous_context}
</context>

<output priority="P0">
【输出格式】
返回第{start_index}-{end_index}节章节规划的JSON数组（共{target_chapter_count}个对象）：

[
  {{
    "sub_index": {start_index},
    "title": "章节标题",
    "plot_summary": "剧情摘要（200-300字）：详细描述该章发生的事件",
    "key_events": ["关键事件1", "关键事件2", "关键事件3"],
    "character_focus": ["角色A", "角色B"],
    "emotional_tone": "情感基调",
    "narrative_goal": "叙事目标",
    "conflict_type": "冲突类型",
    "estimated_words": 3000{scene_field}
  }}
]

【格式规范】
- 纯JSON数组输出，无其他文字
- 内容描述中严禁使用特殊符号
- sub_index从{start_index}开始
</output>

<constraints>
【⚠️ 内容边界约束】
✅ 只能展开当前大纲节点的内容
✅ 深化当前大纲，而非跨越到后续
✅ 放慢叙事节奏

❌ 绝对不能推进到后续大纲内容
❌ 不要让剧情快速推进

【分批连续性约束】
✅ 与前面已生成章节自然衔接
✅ 从第{start_index}节开始编号
✅ 保持叙事连贯性

【🔴 相邻章节差异化约束（防止重复）】
✅ 每章有独特的开场和结束方式
✅ key_events在相邻章节间绝不重叠
✅ plot_summary描述该章独特内容
✅ 特别注意与前序章节的差异化
✅ 避免重复已有内容

【章节间要求】
✅ 与前面章节衔接自然流畅
✅ 剧情递进合理（但不超出当前大纲边界）
✅ 节奏张弛有度
✅ 每章有明确且独特的叙事价值
✅ 关键事件无重叠：检查本批次和前序章节的key_events

【禁止事项】
❌ 输出非JSON格式
❌ 剧情越界到后续大纲
❌ 相邻章节内容重复
❌ 与前序章节key_events雷同
</constraints>"""

    # 章节重写系统提示词 V2（RTCO框架）
    CHAPTER_REGENERATION_SYSTEM = """<system>
你是经验丰富的专业小说编辑和作家，擅长根据反馈意见重新创作章节。
你的任务是根据修改指令，对原始章节进行深度改写和优化。
</system>

<task>
【重写任务】
1. 仔细理解原始章节的内容、情节走向和叙事意图
2. 认真分析所有的修改要求，包括AI分析建议和用户自定义指令
3. 针对每一条修改建议，在新版本中进行具体改进
4. 在保持故事连贯性和角色一致性的前提下，创作改进后的新版本
5. 确保新版本在艺术性、可读性和叙事质量上都有明显提升
</task>

<guidelines>
【改写原则】
- **问题导向**：针对修改指令中指出的每个问题进行改进
- **保持精华**：保留原章节中优秀的描写、对话和情节设计
- **深化细节**：增强场景描写、情感渲染和人物刻画
- **节奏优化**：调整叙事节奏，避免拖沓或过快
- **风格一致**：如果提供了写作风格要求，必须严格遵循

【重点关注】
- 如果修改指令提到"节奏"问题，重点调整叙事速度和场景切换
- 如果修改指令提到"情感"问题，重点深化人物内心戏和情感表达
- 如果修改指令提到"描写"问题，重点丰富环境和动作细节
- 如果修改指令提到"对话"问题，重点让对话更自然、更有个性
- 如果修改指令提到"冲突"问题，重点强化矛盾和戏剧张力
</guidelines>

<output>
【输出规范】
直接输出重写后的章节正文内容。
- 不要包含章节标题、序号或其他元信息
- 不要输出任何解释、注释或创作说明
- 从故事内容直接开始，保持叙事的连贯性
</output>
"""
    # MCP工具测试提示词
    MCP_TOOL_TEST = """你是MCP插件测试助手，需要测试插件 '{plugin_name}' 的功能。

⚠️ 重要规则：生成参数时，必须严格使用工具 schema 中定义的原始参数名称，不要转换为 snake_case 或其他格式。
例如：如果 schema 中是 'nextThoughtNeeded'，就必须使用 'nextThoughtNeeded'，不能改成 'next_thought_needed'。

请选择一个合适的工具进行测试，优先选择搜索、查询类工具。
生成真实有效的测试参数（例如搜索"人工智能最新进展"而不是"test"）。

现在开始测试这个插件。"""

    MCP_TOOL_TEST_SYSTEM = """你是专业的API测试工具。当给定工具列表时，选择一个工具并使用合适的参数调用它。

⚠️ 关键规则：调用工具时，必须严格使用 schema 中定义的原始参数名，不要自行转换命名风格。
- 如果参数名是 camelCase（如 nextThoughtNeeded），就使用 camelCase
- 如果参数名是 snake_case（如 next_thought），就使用 snake_case
- 保持与 schema 中定义的完全一致，包括大小写和命名风格"""
    
    # 灵感模式 - 书名生成（系统提示词）
    INSPIRATION_TITLE_SYSTEM = """你是一位专业的小说创作顾问。
用户的原始想法：{initial_idea}

请根据用户的想法，生成6个吸引人的书名建议，要求：
1. 紧扣用户的原始想法和核心故事构思
2. 富有创意和吸引力
3. 涵盖不同的风格倾向
4. 书名中不要带有"《》"符号

返回JSON格式：
{{
    "prompt": "根据你的想法，我为你准备了几个书名建议：",
    "options": ["书名1", "书名2", "书名3", "书名4", "书名5", "书名6"]
}}

只返回纯JSON，不要有其他文字。"""

    # 灵感模式 - 书名生成（用户提示词）
    INSPIRATION_TITLE_USER = "用户的想法：{initial_idea}\n请生成6个书名建议"

    # 灵感模式 - 简介生成（系统提示词）
    INSPIRATION_DESCRIPTION_SYSTEM = """你是一位专业的小说创作顾问。
用户的原始想法：{initial_idea}
已确定的书名：{title}

请生成6个精彩的小说简介，要求：
1. 必须紧扣用户的原始想法，确保简介是原始想法的具体展开
2. 符合已确定的书名风格
3. 简洁有力，每个50-100字
4. 包含核心冲突
5. 涵盖不同的故事走向，但都基于用户的原始构思

返回JSON格式：
{{"prompt":"选择一个简介：","options":["简介1","简介2","简介3","简介4","简介5","简介6"]}}

只返回纯JSON，不要有其他文字，不要换行。"""

    # 灵感模式 - 简介生成（用户提示词）
    INSPIRATION_DESCRIPTION_USER = "原始想法：{initial_idea}\n书名：{title}\n请生成6个简介选项"

    # 灵感模式 - 主题生成（系统提示词）
    INSPIRATION_THEME_SYSTEM = """你是一位专业的小说创作顾问。
用户的原始想法：{initial_idea}
小说信息：
- 书名：{title}
- 简介：{description}

请生成6个深刻的主题选项，要求：
1. 必须与用户的原始想法保持高度一致
2. 符合书名和简介的风格
3. 有深度和思想性
4. 每个50-150字
5. 涵盖不同角度（如：成长、复仇、救赎、探索等），但都围绕用户的核心构思

返回JSON格式：
{{"prompt":"这本书的核心主题是什么？","options":["主题1","主题2","主题3","主题4","主题5","主题6"]}}

只返回纯JSON，不要有其他文字，不要换行。"""

    # 灵感模式 - 主题生成（用户提示词）
    INSPIRATION_THEME_USER = "原始想法：{initial_idea}\n书名：{title}\n简介：{description}\n请生成6个主题选项"

    # 灵感模式 - 类型生成（系统提示词）
    INSPIRATION_GENRE_SYSTEM = """你是一位专业的小说创作顾问。
用户的原始想法：{initial_idea}
小说信息：
- 书名：{title}
- 简介：{description}
- 主题：{theme}

请从以下预定义类型列表中选择6个最合适的类型标签（可多选组合）：

【预定义类型列表】（必须从中选择，不能生成其他类型）
- 修仙：修仙问道、境界突破、飞升成仙
- 玄幻：异世大陆、血脉觉醒、战力等级
- 仙侠：仙侠世界、剑道修行、斩妖除魔
- 奇幻：魔法世界、种族共存、奇幻冒险
- 灵异：鬼怪悬疑、阴阳两界、驱魔抓鬼
- 武侠：江湖恩怨、武功秘籍、侠义精神
- 历史：历史背景、权谋争斗、朝代更迭
- 都市：都市生活、职场情感、现代背景
- 现代：现代社会、现实题材、生活故事
- 言情：爱情主线、情感纠葛、浪漫故事
- 游戏：游戏世界、电竞竞技、网游小说
- 悬疑：悬疑推理、案件侦破、谜团解开
- 科幻：科技未来、太空探索、科幻设定
- 末世：末日生存、丧尸危机、废土世界

【选择规则】
1. 根据用户原始想法和小说信息，选择最匹配的类型
2. 可以选择多个相关类型组合（如"都市+言情"、"玄幻+修仙"）
3. 必须严格从上述列表中选择，不能创造新类型

返回JSON格式：
{{"prompt":"选择类型标签（可多选）：","options":["类型1","类型2","类型3","类型4","类型5","类型6"]}}

只返回紧凑的纯JSON，不要换行，不要有其他文字。"""

    # 灵感模式 - 类型生成（用户提示词）
    INSPIRATION_GENRE_USER = "原始想法：{initial_idea}\n书名：{title}\n简介：{description}\n主题：{theme}\n请从预定义列表中选择6个类型标签"

    # 灵感模式智能补全提示词
    INSPIRATION_QUICK_COMPLETE = """你是一位专业的小说创作顾问。用户提供了部分小说信息，请补全缺失的字段。

用户已提供的信息：
{existing}

请生成完整的小说方案，包含：
1. title: 书名（3-6字，如果用户已提供则保持原样）
2. description: 简介（50-100字，必须基于用户提供的信息，不要偏离原意）
3. theme: 核心主题（30-50字，必须与用户提供的信息保持一致）
4. genre: 类型标签数组（必须从以下预定义列表中选择2-3个）

【预定义类型列表】
修仙、玄幻、仙侠、奇幻、灵异、武侠、历史、都市、现代、言情、游戏、悬疑、科幻、末世

重要：所有补全的内容都必须与用户提供的信息保持高度关联，确保前后一致性。genre必须从预定义列表中选择。

返回JSON格式：
{{
    "title": "书名",
    "description": "简介内容...",
    "theme": "主题内容...",
    "genre": ["类型1", "类型2"]
}}

只返回纯JSON，不要有其他文字。"""

    # 物品分析提示词
    ITEM_ANALYSIS = """<system>
你是专业的小说物品分析师，擅长从章节内容中识别和追踪物品的出现、流转和状态变化。
</system>

<task>
【分析任务】
分析第{chapter_number}章「{title}」中的物品相关信息，识别物品的出现、流转、状态变化和数量变更。

【分析重点】
{analysis_requirements}
</task>

<input priority="P0">
【章节内容】
{content}
</input>

<existing_items priority="P1">
【已有物品列表】
以下是项目中已存在的物品，请在识别时尝试匹配（使用完全相同的名称）：
{existing_items}

**匹配规则**：
- 如果识别的物品名称与已有物品名称或别名完全一致，填写reference_item_id
- 新出现的物品不填写reference_item_id
</existing_items>

<categories_info priority="P2">
【分类信息】
以下是项目的物品分类体系，新物品建议选择合适的分类：
{categories_info}
</categories_info>

<analysis_framework>
请仔细阅读章节内容，识别以下物品相关信息：

**⚠️ 重要规则：分开识别多个物品**
当一句话中出现多个不同的物品时，必须将每个物品分开识别为独立的条目。
- ❌ 错误示例："三十块下品灵石和五瓶劣质聚气丹" → 物品名称："下品灵石与聚气丹"，数量：35
- ✅ 正确示例：
  - 物品名称："下品灵石"，数量：30
  - 物品名称："劣质聚气丹"，数量：5
**每个物品必须是独立的个体，即使它们同时出现或属于同一批发放。**

**1. 新出现物品**
首次在本章节登场的物品：
- 物品名称
- 物品类型（weapon/armor/consumable/material/artifact/other）
- 出现方式（appear/find/craft/buy/obtain）
- 初始归属（哪个角色获得）
- 数量信息
- 物品描述（外观、功能）

**2. 物品流转**
已有物品的持有权发生变化：
- 物品名称（必须与已有物品列表中的名称一致）
- 原持有者 → 新持有者
- 流转方式（transfer/give/trade/steal/loot/inherit）
- 流转描述

**3. 物品状态变化**
物品状态发生改变：
- 装备(equip)/卸下(unequip)
- 消耗(consume)/使用(use)
- 销毁(destroy)
- 丢失(lose)
- 封印(seal)

**4. 数量变更**
消耗品等可堆叠物品的数量变化：
- 物品名称
- 使用/消耗数量
- 剩余数量

**5. AI可提取的物品属性**
尽可能从原文中提取以下属性：
- rarity: 稀有度（common/uncommon/rare/epic/legendary/artifact）
- quality: 品质（如：上品、极品、残缺、完美）
- special_effects: 特殊效果描述
- lore: 背景故事/来历
- value: 价值（金币数）
- aliases: 别名/别称列表
- attributes: 属性数值（如：{{"攻击力": 120, "防御力": 50}}）
- is_plot_critical: 是否剧情关键物品（对主线有重要影响）
- unit: 计量单位（如：个、颗、把、张）
- suggested_category: 建议分类名称
</analysis_framework>

<output priority="P0">
【输出格式】
返回纯JSON对象（无markdown标记）：

{{
  "items": [
    {{
      "item_name": "物品名称",
      "item_type": "物品类型",
      "event_type": "事件类型",
      "reference_item_id": "匹配的已有物品ID（新物品为null）",
      "from_character": "原持有者（转移时必填）",
      "to_character": "新持有者",
      "quantity_change": 数量变化（正数增加，负数减少）,
      "quantity_after": 变化后数量,
      "description": "详细描述物品变化过程",
      "keyword": "原文定位关键词（8-25字）",
      "rarity": "稀有度",
      "quality": "品质",
      "special_effects": "特殊效果描述",
      "lore": "背景故事",
      "value": 价值,
      "aliases": ["别名1", "别名2"],
      "attributes": {{}},
      "is_plot_critical": 是否剧情关键,
      "unit": "计量单位",
      "suggested_category": "建议分类名称"
    }}
  ],
  "summary": "本章节物品变化概述（50字以内）"
}}

【正确示例：多个物品分开识别】
原文："庶务堂发放给林渊的本月修炼资源，包括三十块下品灵石和五瓶最劣质的聚气丹。"

正确输出：
{{
  "items": [
    {{
      "item_name": "下品灵石",
      "item_type": "material",
      "event_type": "obtain",
      "to_character": "林渊",
      "quantity_change": 30,
      "quantity_after": 30,
      "description": "庶务堂发放给林渊的本月修炼资源",
      "keyword": "三十块下品灵石",
      "rarity": "common",
      "unit": "块",
      "suggested_category": "材料"
    }},
    {{
      "item_name": "劣质聚气丹",
      "item_type": "consumable",
      "event_type": "obtain",
      "to_character": "林渊",
      "quantity_change": 5,
      "quantity_after": 5,
      "description": "庶务堂发放的最劣质聚气丹",
      "keyword": "五瓶最劣质的聚气丹",
      "rarity": "common",
      "quality": "劣质",
      "unit": "瓶",
      "suggested_category": "丹药"
    }}
  ],
  "summary": "林渊从庶务堂获得下品灵石30块和劣质聚气丹5瓶"
}}

如果本章节无物品相关内容，返回：
{{"items": [], "summary": "本章节无物品相关内容"}}
</output>"""

    # 世界观资料收集提示词（MCP增强用）
    MCP_WORLD_BUILDING_PLANNING = """你正在为小说《{title}》设计世界观。

【小说信息】
- 题材：{genre}
- 主题：{theme}
- 简介：{description}

【任务】
请使用可用工具搜索相关背景资料，帮助构建更真实、更有深度的世界观设定。
你可以查询：
1. 历史背景（如果是历史题材）
2. 地理环境和文化特征
3. 相关领域的专业知识
4. 类似作品的设定参考

请查询最关键的1个问题（不要超过1个）。"""

    # 角色资料收集提示词（MCP增强用）
    MCP_CHARACTER_PLANNING = """你正在为小说《{title}》设计角色。

【小说信息】
- 题材：{genre}
- 主题：{theme}
- 时代背景：{time_period}
- 地理位置：{location}

【任务】
请使用可用工具搜索相关参考资料，帮助设计更真实、更有深度的角色。
你可以查询：
1. 该时代/地域的真实历史人物特征
2. 文化背景和社会习俗
3. 职业特点和生活方式
4. 相关领域的人物原型

请查询最关键的1个问题（不要超过1个）。"""

    # 自动角色引入 - 预测性分析提示词 V2（RTCO框架）
    AUTO_CHARACTER_ANALYSIS = """<system>
你是专业的小说角色设计顾问，擅长预测剧情发展对角色的需求。
</system>

<task>
【分析任务】
预测在接下来的{chapter_count}章续写中，根据剧情发展方向和阶段，是否需要引入新角色。

【重要说明】
这是预测性分析，而非基于已生成内容的事后分析。
</task>

<project priority="P1">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}

【世界观】
时间背景：{time_period}
地理位置：{location}
氛围基调：{atmosphere}
</project>

<context priority="P0">
【已有角色】
{existing_characters}

【已有章节概览】
{all_chapters_brief}

【续写计划】
- 起始章节：第{start_chapter}章
- 续写数量：{chapter_count}章
- 剧情阶段：{plot_stage}
- 发展方向：{story_direction}
</context>

<analysis_framework priority="P0">
【预测分析维度】

**1. 剧情需求预测**
根据发展方向，哪些场景、冲突需要新角色参与？

**2. 角色充分性**
现有角色是否足以支撑即将发生的剧情？

**3. 引入时机**
新角色应该在哪个章节登场最合适？

**4. 重要性判断**
新角色对后续剧情的影响程度如何？

【预测依据】
- 剧情阶段的典型角色需求（如：高潮阶段可能需要强力对手）
- 故事发展方向的逻辑需要（如：进入新地点需要当地角色）
- 冲突升级的角色需求（如：更强的反派、意外的盟友）
- 世界观扩展的需要（如：新组织、新势力的代表）
</analysis_framework>

<output priority="P0">
【输出格式】
返回纯JSON对象（两种情况之一）：

**情况A：需要新角色**
{{
  "needs_new_characters": true,
  "reason": "预测分析原因（150-200字），说明为什么即将的剧情需要新角色",
  "character_count": 2,
  "character_specifications": [
    {{
      "name": "建议的角色名字（可选）",
      "role_description": "角色在剧情中的定位和作用（100-150字）",
      "suggested_role_type": "supporting/antagonist/protagonist",
      "importance": "high/medium/low",
      "appearance_chapter": {start_chapter},
      "key_abilities": ["能力1", "能力2"],
      "plot_function": "在剧情中的具体功能",
      "relationship_suggestions": [
        {{
          "target_character": "现有角色名",
          "relationship_type": "建议的关系类型",
          "reason": "为什么建立这种关系"
        }}
      ]
    }}
  ]
}}

**情况B：不需要新角色**
{{
  "needs_new_characters": false,
  "reason": "现有角色足以支撑即将的剧情发展，说明理由"
}}
</output>

<constraints>
【必须遵守】
✅ 这是预测性分析，面向未来剧情
✅ 考虑剧情的自然发展和节奏
✅ 确保引入必要性，不为引入而引入
✅ 优先考虑角色的长期作用

【禁止事项】
❌ 输出markdown标记
❌ 基于已生成内容做事后分析
❌ 为了引入角色而强行引入
❌ 设计一次性功能角色
</constraints>"""

    # 自动角色引入 - 生成提示词 V2（RTCO框架）
    AUTO_CHARACTER_GENERATION = """<system>
你是专业的角色设定师，擅长根据剧情需求创建完整的角色设定。
</system>

<task>
【生成任务】
为小说生成新角色的完整设定，包括基本信息、性格背景、关系网络和职业信息。
</task>

<project priority="P1">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}

【世界观设定】
{world_setting}
</project>

<context priority="P0">
【已有角色】
{existing_characters}

【剧情上下文】
{plot_context}

【角色规格要求】
{character_specification}
</context>

<mcp_context priority="P2">
【MCP工具参考】
{mcp_references}
</mcp_context>

<requirements priority="P0">
【核心要求】
1. 角色必须符合剧情需求和世界观设定
2. **必须分析新角色与已有角色的关系**，至少建立1-3个有意义的关系
3. 性格、背景要有深度和独特性
4. 外貌描写要具体生动
5. 特长和能力要符合角色定位
6. **如果【已有角色】中包含职业列表，必须为角色设定职业**

【关系建立指导】
- 仔细审视【已有角色】列表，思考新角色与哪些现有角色有联系
- 根据剧情需求，建立合理的角色关系
- 每个关系都要有明确的类型、亲密度和描述
- 关系应该服务于剧情发展
- 如果新角色是组织成员，记得填写organization_memberships

【职业信息要求】
如果【已有角色】部分包含"可用主职业列表"或"可用副职业列表"：
- 仔细查看可用的主职业和副职业列表
- 根据角色的背景、能力、故事定位，选择最合适的职业
- 主职业：从"可用主职业列表"中选择一个，填写职业名称
- 主职业阶段：根据职业的阶段信息和角色实力，设定合理的当前阶段
- 副职业：可选择0-2个副职业
- ⚠️ 重要：必须填写职业的名称而非ID
</requirements>

<output priority="P0">
【输出格式】
返回纯JSON对象：

{{
  "name": "角色姓名",
  "age": 25,
  "gender": "男/女/其他",
  "role_type": "supporting",
  "personality": "性格特点的详细描述（100-200字）",
  "background": "背景故事的详细描述（100-200字）",
  "appearance": "外貌描述（50-100字）",
  "traits": ["特长1", "特长2", "特长3"],
  "relationships_text": "用自然语言描述该角色与其他角色的关系网络",
  
  "relationships": [
    {{
      "target_character_name": "已存在的角色名称",
      "relationship_type": "关系类型",
      "intimacy_level": 75,
      "description": "关系的具体描述",
      "status": "active"
    }}
  ],
  "organization_memberships": [
    {{
      "organization_name": "已存在的组织名称",
      "position": "职位",
      "rank": 5,
      "loyalty": 80
    }}
  ],
  
  "career_info": {{
    "main_career_name": "从可用主职业列表中选择的职业名称",
    "main_career_stage": 5,
    "sub_careers": [
      {{
        "career_name": "从可用副职业列表中选择的职业名称",
        "stage": 3
      }}
    ]
  }}
}}

【关系类型参考】
家族、社交、职业、敌对等各类关系

【数值范围】
- intimacy_level：-100到100（负值表示敌对）
- loyalty：0到100
- rank：0到10
</output>

<constraints>
【必须遵守】
✅ 符合剧情需求和世界观设定
✅ relationships数组必填：至少1-3个关系
✅ target_character_name必须精确匹配【已有角色】
✅ organization_memberships只能引用已存在的组织
✅ 职业选择必须从可用列表中选择

【禁止事项】
❌ 输出markdown标记
❌ 在描述中使用特殊符号
❌ 引用不存在的角色或组织
❌ 使用职业ID而非职业名称
</constraints>"""

    # 自动组织引入 - 预测性分析提示词（RTCO框架）
    AUTO_ORGANIZATION_ANALYSIS = """<system>
你是专业的小说世界构建顾问，擅长预测剧情发展对组织/势力的需求。
</system>

<task>
【分析任务】
预测在接下来的{chapter_count}章续写中，根据剧情发展方向和阶段，是否需要引入新的组织或势力。

【重要说明】
这是预测性分析，而非基于已生成内容的事后分析。
组织包括：帮派、门派、公司、政府机构、神秘组织、家族等。
</task>

<project priority="P1">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}

【世界观】
时间背景：{time_period}
地理位置：{location}
氛围基调：{atmosphere}
</project>

<context priority="P0">
【已有组织】
{existing_organizations}

【已有角色】
{existing_characters}

【已有章节概览】
{all_chapters_brief}

【续写计划】
- 起始章节：第{start_chapter}章
- 续写数量：{chapter_count}章
- 剧情阶段：{plot_stage}
- 发展方向：{story_direction}
</context>

<analysis_framework priority="P0">
【预测分析维度】

**1. 世界观扩展需求**
根据发展方向，是否需要新的势力或组织来丰富世界观？

**2. 冲突升级需求**
剧情是否需要新的对立势力、竞争组织或神秘集团？

**3. 角色归属需求**
现有角色是否需要加入或对抗某个新组织？

**4. 剧情推动需求**
新组织能否成为推动剧情的关键力量？

**5. 引入时机**
新组织应该在哪个章节出现最合适？

【预测依据】
- 剧情阶段的典型组织需求（如：高潮阶段可能需要强大的敌对势力）
- 故事发展方向的逻辑需要（如：进入新地点需要当地势力）
- 世界观完整性需要（如：权力格局需要多方势力）
- 角色成长需要（如：主角需要加入或创建组织）
</analysis_framework>

<output priority="P0">
【输出格式】
返回纯JSON对象（两种情况之一）：

**情况A：需要新组织**
{{
"needs_new_organizations": true,
"reason": "预测分析原因（150-200字），说明为什么即将的剧情需要新组织",
"organization_count": 1,
"organization_specifications": [
{{
  "name": "建议的组织名字（可选）",
  "organization_description": "组织在剧情中的定位和作用（100-150字）",
  "organization_type": "帮派/门派/公司/政府/家族/神秘组织等",
  "importance": "high/medium/low",
  "appearance_chapter": {start_chapter},
  "power_level": 70,
  "plot_function": "在剧情中的具体功能",
  "location": "组织所在地或活动区域",
  "motto": "组织口号或宗旨（可选）",
  "initial_members": [
    {{
      "character_name": "现有角色名（如需加入）",
      "position": "职位",
      "reason": "为什么加入"
    }}
  ],
  "relationship_suggestions": [
    {{
      "target_organization": "已有组织名",
      "relationship_type": "建议的关系类型（盟友/敌对/竞争/合作等）",
      "reason": "为什么建立这种关系"
    }}
  ]
}}
]
}}

**情况B：不需要新组织**
{{
"needs_new_organizations": false,
"reason": "现有组织足以支撑即将的剧情发展，说明理由"
}}
</output>

<constraints>
【必须遵守】
✅ 这是预测性分析，面向未来剧情
✅ 考虑世界观的丰富性和完整性
✅ 确保引入必要性，不为引入而引入
✅ 优先考虑组织的长期作用
✅ 组织应该是推动剧情的关键力量

【禁止事项】
❌ 输出markdown标记
❌ 基于已生成内容做事后分析
❌ 为了引入组织而强行引入
❌ 设计一次性功能组织
❌ 创建与现有组织功能重复的组织
</constraints>"""

    # 自动组织引入 - 生成提示词（RTCO框架）
    AUTO_ORGANIZATION_GENERATION = """<system>
你是专业的世界构建师，擅长根据剧情需求创建完整的组织/势力设定。
</system>

<task>
【生成任务】
为小说生成新组织的完整设定，包括基本信息、组织特性、背景历史和成员结构。
</task>

<project priority="P1">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}

【世界观设定】
{world_setting}
</project>

<context priority="P0">
【已有组织】
{existing_organizations}

【已有角色】
{existing_characters}

【剧情上下文】
{plot_context}

【组织规格要求】
{organization_specification}
</context>

<mcp_context priority="P2">
【MCP工具参考】
{mcp_references}
</mcp_context>

<requirements priority="P0">
【核心要求】
1. 组织必须符合剧情需求和世界观设定
2. 组织要有明确的目的、结构和特色
3. 组织特性、背景要有深度和独特性
4. 外在表现要具体生动
5. 考虑与已有组织的关系和互动
6. 如果需要，可以建议将现有角色加入组织
</requirements>

<output priority="P0">
【输出格式】
返回纯JSON对象：

{{
"name": "组织名称",
"is_organization": true,
"role_type": "supporting",
"organization_type": "组织类型（帮派/门派/公司/政府/家族/神秘组织等）",
"personality": "组织特性的详细描述（150-200字）：运作方式、核心理念、行事风格、文化价值观",
"background": "组织背景故事（200-300字）：建立历史、发展历程、重要事件、当前地位",
"appearance": "外在表现（100-150字）：总部位置、标志性建筑、组织标志、成员着装",
"organization_purpose": "组织目的和宗旨：明确目标、长期愿景、行动准则",
"power_level": 75,
"location": "所在地点：主要活动区域、势力范围",
"motto": "组织格言或口号",
"color": "组织代表颜色",
"traits": ["特征1", "特征2", "特征3"],

"initial_members": [
{{
  "character_name": "已存在的角色名称",
  "position": "职位名称",
  "rank": 8,
  "loyalty": 80,
  "joined_at": "加入时间（可选）",
  "status": "active"
}}
],

"organization_relationships": [
{{
  "target_organization_name": "已存在的组织名称",
  "relationship_type": "盟友/敌对/竞争/合作/从属等",
  "description": "关系的具体描述"
}}
]
}}

【数值范围】
- power_level：0-100的整数，表示在世界中的影响力
- rank：0到10（职位等级）
- loyalty：0到100（成员忠诚度）
</output>

<constraints>
【必须遵守】
✅ 符合剧情需求和世界观设定
✅ 组织要有独特的定位和价值
✅ character_name必须精确匹配【已有角色】
✅ target_organization_name必须精确匹配【已有组织】
✅ 组织能够推动剧情发展

【禁止事项】
❌ 输出markdown标记
❌ 在描述中使用特殊符号
❌ 引用不存在的角色或组织
❌ 创建功能与现有组织重复的组织
❌ 创建对剧情没有实际作用的组织
</constraints>"""

    # 职业体系生成提示词 V2（RTCO框架）
    CAREER_SYSTEM_GENERATION = """<system>
你是专业的职业体系设计师，擅长为不同世界观设计完整的职业体系。
</system>

<task>
【设计任务】
根据世界观信息和项目简介，设计一个完整且合理的职业体系。
职业体系必须与项目简介中的故事背景和角色设定高度契合。

【数量要求】
- 主职业：精确生成3个
- 副职业：精确生成2个
</task>

<worldview priority="P0">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
简介：{description}

【世界观设定】
{world_setting}

{attribute_schema_info}
</worldview>

<design_requirements priority="P0">
【设计要求】

**1. 主职业（main_careers）- 必须精确生成3个**
- 主职业是角色的核心发展方向
- 必须严格符合世界观规则和简介中的故事背景
- 3个主职业应该覆盖不同的发展路线（如：战斗型、智慧型、特殊型）
- 每个主职业的阶段数量可以不同（体现职业复杂度差异）
- 职业设计要能支撑简介中描述的故事情节

**2. 副职业（sub_careers）- 必须精确生成2个**
- 副职业包含生产、辅助、特殊技能类
- 2个副职业应该具有互补性，丰富角色的多样性
- 每个副职业的阶段数量可以不同
- 不要让所有副职业都是相同的阶段数
- 副职业要能为主职业提供辅助或增益

**3. 阶段设计（stages）**
- 每个职业的stages数组长度必须等于max_stage
- 阶段名称必须使用项目定义的阶段名称（如上面的能力属性体系中列出的阶段）
- 阶段描述要体现明确的能力提升路径
- 确保职业间的阶段数量有差异
- 主职业阶段数建议：8-12个
- 副职业阶段数建议：5-8个

**4. 属性配置**
- base_attributes：选择该职业时的初始能力值，属性名必须使用项目定义的数值型属性名
- per_stage_bonus：每晋升一阶段增加的能力值，格式为 {{ "属性名": {{ "per_stage": 增加值 }} }}

**5. 简介契合度**
- 职业体系必须与项目简介中的故事设定相匹配
- 如果简介中提到特定职业或能力，优先设计相关职业
- 职业的能力和特点要能支撑简介中的情节发展
</design_requirements>

<output priority="P0">
【输出格式】
返回纯JSON对象：

{{
"main_careers": [
{{
  "name": "职业名称",
  "description": "职业描述（100-150字）",
  "category": "职业分类",
  "stages": [
    {{"level": 1, "name": "{stage_example}", "description": "阶段描述"}},
    {{"level": 2, "name": "第二阶段名称", "description": "阶段描述"}}
  ],
  "max_stage": 整数,
  "requirements": "职业要求和前置条件",
  "special_abilities": "职业特殊能力",
  "worldview_rules": "与世界观规则的关联",
  "base_attributes": {{ "{attr_example_name}": 60 }},
  "per_stage_bonus": {{ "{attr_example_name}": {{ "per_stage": 10 }} }}
}}
],
"sub_careers": [
{{
  "name": "副职业名称",
  "description": "职业描述（80-120字）",
  "category": "生产系/辅助系/特殊系",
  "stages": [
    {{"level": 1, "name": "入门", "description": "阶段描述"}}
  ],
  "max_stage": 整数,
  "requirements": "职业要求",
  "special_abilities": "特殊能力",
  "base_attributes": {{ "{attr_example_name}": 30 }},
  "per_stage_bonus": {{ "{attr_example_name}": {{ "per_stage": 5 }} }}
}}
]
}}
</output>

<constraints>
【必须遵守】
✅ 主职业数量：必须精确生成3个，不多不少
✅ 副职业数量：必须精确生成2个，不多不少
✅ 不同职业的max_stage必须不同
✅ 主职业阶段数建议：8-12个
✅ 副职业阶段数建议：5-8个
✅ stages数组长度必须等于max_stage
✅ 阶段名称必须使用项目定义的阶段名称
✅ 属性名必须使用项目定义的数值型属性名
✅ 确保职业体系与世界观高度契合
✅ 职业设计必须支撑项目简介中的故事情节

【禁止事项】
❌ 生成超过3个主职业或少于3个主职业
❌ 生成超过2个副职业或少于2个副职业
❌ 所有职业使用相同的阶段数
❌ 输出markdown标记
❌ 职业设计与世界观或简介脱节
❌ 忽略简介中提到的职业或能力设定
❌ 使用不在项目属性定义中的属性名
</constraints>"""

    # 局部重写提示词（RTCO框架）
    PARTIAL_REGENERATE = """<system>
你是一位专业的小说改写助手，擅长根据用户的修改要求精准改写指定段落，同时确保与前后文无缝衔接。
</system>

<task>
【改写任务】
根据用户的修改要求，重写下面选中的文本段落。

【重要要求】
1. 只输出重写后的内容，不要包含任何解释、前缀或后缀
2. 保持与前后文的自然衔接和语气连贯
3. 严格遵循用户的修改要求
4. 保持整体叙事风格的一致性
</task>

<context priority="P0">
【前文参考】（用于衔接，勿重复）
{context_before}

【需要重写的原文】（共{original_word_count}字）
{selected_text}

【后文参考】（用于衔接，勿重复）
{context_after}
</context>

<user_requirements priority="P0">
【用户修改要求】
{user_instructions}

【字数要求】
{length_requirement}
</user_requirements>

<style priority="P1">
【写作风格】
{style_content}
</style>

<output>
【输出规范】
直接输出重写后的内容，从故事内容开始写。
- 不要输出任何解释或说明文字
- 不要输出"重写后："等前缀
- 不要输出引号包裹内容
- 确保输出内容可以直接替换原文

请直接输出重写后的内容：
</output>

<constraints>
【必须遵守】
✅ 前后衔接：输出内容必须与前文自然衔接，与后文平滑过渡
✅ 风格一致：保持与原文相同的叙事风格、语气和人称
✅ 要求优先：严格执行用户的修改要求
✅ 字数控制：遵循字数要求

【禁止事项】
❌ 重复前文内容
❌ 重复后文内容
❌ 添加任何元信息或说明
❌ 改变叙事人称或视角
❌ 偏离用户的修改要求
</constraints>"""

    # 拆书导入-反向项目提炼提示词
    BOOK_IMPORT_REVERSE_PROJECT_SUGGESTION = """<system>
你是资深网文策划编辑，擅长从小说正文中反向提炼项目立项信息。
</system>

<task>
【任务】
基于提供的前3章内容，提炼该小说的核心立项信息，用于创建新项目。

【目标】
在不偏离原文的前提下，输出可直接用于项目初始化的结构化信息。
</task>

<input priority="P0">
【输入信息】
书名：{title}
前3章内容：
{sampled_text}
</input>

<output priority="P0">
【输出格式】
仅输出一个纯JSON对象（不要markdown、不要代码块、不要解释）：

{{
  "description": "小说简介",
  "theme": "核心主题",
  "genre": "小说类型",
  "narrative_perspective": "第一人称/第三人称/全知视角",
  "target_words": 100000
}}

【字段要求】
1) description：120-260字，聚焦主角、核心冲突、主线目标与故事张力。
2) theme：120-260字，提炼作品想表达的核心命题。
3) genre：2-12字，如都市、玄幻、悬疑、科幻、言情等。
4) narrative_perspective：只能是“第一人称”或“第三人称”或“全知视角”。
5) target_words：整数。按网文体量合理预估；无法判断时返回100000。
</output>

<constraints>
【必须遵守】
✅ 严格基于已给正文内容，不凭空添加关键设定
✅ 保持信息自洽，避免互相矛盾
✅ 输出必须是可解析JSON对象
✅ 小说的genre可以由多个类型组成

【禁止事项】
❌ 输出JSON以外的任何文字
❌ 使用markdown标记或代码块包裹
❌ narrative_perspective输出枚举值之外的内容
❌ target_words输出非整数
</constraints>"""

    # 拆书导入-反向生成章节大纲（严格对齐 OUTLINE_CREATE 结构）
    BOOK_IMPORT_REVERSE_OUTLINES = """<system>
你是资深网文总编与剧情策划，擅长基于已完成章节反向提炼标准化章节大纲。
</system>

<task>
【任务】
基于给定的章节正文（每批最多5章），为每章反向生成对应大纲结构。

【核心目标】
输出结构必须与系统现有大纲生成结构严格一致（与 OUTLINE_CREATE 字段一致），用于直接入库。
</task>

<project priority="P0">
【项目信息】
书名：{title}
类型：{genre}
主题：{theme}
叙事视角：{narrative_perspective}
</project>

<input priority="P0">
【批次范围】
第{start_chapter}章 - 第{end_chapter}章（共{expected_count}章）

【章节内容】
{chapters_text}
</input>

<output priority="P0">
【输出格式】
仅输出纯JSON数组（不要markdown、不要代码块、不要解释）。
数组长度必须严格等于 {expected_count}。

每个对象字段必须严格为：
[
  {{
    "chapter_number": 1,
    "title": "章节标题",
    "summary": "章节概要（200-600字）：主要情节、角色互动、关键事件、冲突与转折",
    "scenes": ["场景1描述", "场景2描述"],
    "characters": [
      {{"name": "角色名1", "type": "character"}},
      {{"name": "组织/势力名1", "type": "organization"}}
    ],
    "key_points": ["情节要点1", "情节要点2"],
    "emotion": "本章情感基调",
    "goal": "本章叙事目标"
  }}
]

【字段约束】
- chapter_number：必须与输入章节号一致
- title：必须与输入章节标题一致
- summary：根据本章正文反向提炼，不得臆造未出现关键事件
- scenes：2-6条
- characters：可为空；type 仅允许 character 或 organization
- key_points：2-6条
- emotion：一句话
- goal：一句话
</output>

<constraints>
【必须遵守】
✅ 严格一章对应一个对象，数量与顺序完全一致
✅ 字段名、字段层级、字段类型严格一致
✅ 仅基于输入正文提炼，不擅自扩展设定
✅ 输出必须可被JSON直接解析

【禁止事项】
❌ 输出JSON之外任何文本
❌ 缺失字段或新增字段
❌ chapter_number/title 与输入不一致
❌ 使用 markdown 或代码块
</constraints>"""

    @staticmethod
    def format_prompt(template: str, **kwargs) -> str:
        """
        格式化提示词模板
        
        Args:
            template: 提示词模板
            **kwargs: 模板参数
            
        Returns:
            格式化后的提示词
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"缺少必需的参数: {e}")
    

    @classmethod
    async def get_chapter_regeneration_prompt(cls, chapter_number: int, title: str, word_count: int, content: str,
                                        modification_instructions: str, project_context: Dict[str, Any],
                                        style_content: str, target_word_count: int,
                                        user_id: Optional[str] = None, db = None) -> str:
        """
        获取章节重写提示词（支持用户自定义）
        
        Args:
            chapter_number: 章节序号
            title: 章节标题
            word_count: 原始字数
            content: 原始内容
            modification_instructions: 修改指令
            project_context: 项目上下文
            style_content: 写作风格
            target_word_count: 目标字数
            user_id: 用户ID（可选，用于获取自定义模板）
            db: 数据库会话（可选，用于查询自定义模板）
            
        Returns:
            完整的章节重写提示词
        """
        # 获取系统提示词模板（支持用户自定义）
        if user_id and db:
            system_template = await cls.get_template("CHAPTER_REGENERATION_SYSTEM", user_id, db) or cls.CHAPTER_REGENERATION_SYSTEM
        else:
            system_template = cls.CHAPTER_REGENERATION_SYSTEM

        prompt_parts: list[str] = [system_template]
        
        # 原始章节信息
        prompt_parts.append(f"""## 📖 原始章节信息

**章节**：第{chapter_number}章
**标题**：{title}
**字数**：{word_count}字

**原始内容**：
{content}

---
""")
        
        # 修改指令
        prompt_parts.append(modification_instructions)
        prompt_parts.append("\n---\n")
        
        # 项目背景信息
        prompt_parts.append(f"""## 🌍 项目背景信息

**小说标题**：{project_context.get('project_title', '未知')}
**题材**：{project_context.get('genre', '未设定')}
**主题**：{project_context.get('theme', '未设定')}
**叙事视角**：{project_context.get('narrative_perspective', '第三人称')}
**世界观设定**：
{project_context.get('world_setting', '未设定')}

---
""")
        
        # 角色信息
        if project_context.get('characters_info'):
            prompt_parts.append(f"""## 👥 角色信息

{project_context['characters_info']}

---
""")
        
        # 章节大纲
        if project_context.get('chapter_outline'):
            prompt_parts.append(f"""## 📝 本章大纲

{project_context['chapter_outline']}

---
""")
        
        # 前置章节上下文
        if project_context.get('previous_context'):
            prompt_parts.append(f"""## 📚 前置章节上下文

{project_context['previous_context']}

---
""")
        
        # 写作风格要求
        if style_content:
            prompt_parts.append(f"""## 🎨 写作风格要求

{style_content}

请在重新创作时严格遵循上述写作风格。

---
""")
        
        # 创作要求
        prompt_parts.append(f"""## ✨ 创作要求

1. **解决问题**：针对上述修改指令中提到的所有问题进行改进
2. **保持连贯**：确保与前后章节的情节、人物、风格保持一致
3. **提升质量**：在节奏、情感、描写等方面明显优于原版
4. **保留精华**：保持原章节中优秀的部分和关键情节
5. **字数控制**：目标字数约{target_word_count}字（可适当浮动±20%）
{f'6. **风格一致**：严格按照上述写作风格进行创作' if style_content else ''}

---

## 🎬 开始创作

请现在开始创作改进后的新版本章节内容。

**重要提示**：
- 直接输出章节正文内容，从故事内容开始写
- **不要**输出章节标题（如"第X章"、"第X章：XXX"等）
- **不要**输出任何额外的说明、注释或元数据
- 只需要纯粹的故事正文内容

现在开始：
""")
        
        return "\n".join(prompt_parts)

    @classmethod
    async def get_mcp_tool_test_prompts(
        cls,
        plugin_name: str,
        user_id: Optional[str] = None,
        db = None
    ) -> Dict[str, str]:
        """
        获取MCP工具测试的提示词（支持自定义）
        
        Args:
            plugin_name: 插件名称
            user_id: 用户ID（可选）
            db: 数据库会话（可选）
            
        Returns:
            包含user和system提示词的字典
        """
        # 获取用户自定义或系统默认的user提示词
        if user_id and db:
            user_template = await cls.get_template("MCP_TOOL_TEST", user_id, db) or cls.MCP_TOOL_TEST
        else:
            user_template = cls.MCP_TOOL_TEST

        # 获取用户自定义或系统默认的system提示词
        if user_id and db:
            system_template = await cls.get_template("MCP_TOOL_TEST_SYSTEM", user_id, db) or cls.MCP_TOOL_TEST_SYSTEM
        else:
            system_template = cls.MCP_TOOL_TEST_SYSTEM

        return {
            "user": cls.format_prompt(user_template, plugin_name=plugin_name),
            "system": system_template
        }

    # ========== 自定义提示词支持 ==========
    
    @classmethod
    async def get_template_with_fallback(cls,
                                        template_key: str,
                                        user_id: Optional[str] = None,
                                        db = None) -> Optional[str]:
        """
        获取提示词模板（优先用户自定义，支持降级）
        
        Args:
            template_key: 模板键名
            user_id: 用户ID（可选，如果不提供则直接返回系统默认）
            db: 数据库会话（可选）
            
        Returns:
            提示词模板内容
        """
        # 如果没有提供user_id或db，直接返回系统默认
        if not user_id or not db:
            return getattr(cls, template_key, None)
        
        # 尝试获取用户自定义模板
        return await cls.get_template(template_key, user_id, db)
    
    @classmethod
    async def get_template(cls,
                          template_key: str,
                          user_id: str,
                          db) -> Optional[str]:
        """
        获取提示词模板（优先用户自定义）
        
        Args:
            template_key: 模板键名
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            提示词模板内容
        """
        from sqlalchemy import select
        from app.models.prompt_template import PromptTemplate
        from app.logger import get_logger
        
        logger = get_logger(__name__)
        
        # 1. 尝试从数据库获取用户自定义模板
        result = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.user_id == user_id,
                PromptTemplate.template_key == template_key,
                PromptTemplate.is_active == True
            )
        )
        custom_template = result.scalar_one_or_none()
        
        if custom_template:
            logger.info(f"✅ 使用用户自定义提示词: user_id={user_id}, template_key={template_key}, template_name={custom_template.template_name}")
            return custom_template.template_content
        
        # 2. 降级到系统默认模板
        logger.info(f"⚪ 使用系统默认提示词: user_id={user_id}, template_key={template_key} (未找到自定义模板)")
        
        # 直接从类属性获取系统默认模板
        template_content = getattr(cls, template_key, None)
        
        if template_content is None:
            logger.warning(f"⚠️ 未找到系统默认模板: {template_key}")
        
        return template_content
    
    @classmethod
    def get_all_system_templates(cls) -> list:
        """
        获取所有系统默认模板的信息
        
        Returns:
            系统模板列表
        """
        templates = []
        
        # 定义所有模板及其元信息
        template_definitions = {
            "WORLD_BUILDING": {
                "name": "世界构建",
                "category": "世界构建",
                "description": "用于生成小说世界观设定，包括时间背景、地理位置、氛围基调和世界规则",
                "parameters": ["title", "theme", "genre", "description"]
            },
            "WORLD_BUILDING_V2": {
                "name": "世界构建(V2)",
                "category": "世界构建",
                "description": "V2版本世界构建，生成核心结构(地点、势力、力量体系)和概述字段",
                "parameters": ["title", "theme", "genre", "description", "chapter_count", "narrative_perspective"]
            },
            "WORLD_BUILDING_V3_CORE": {
                "name": "世界构建(V3-核心阶段)",
                "category": "世界构建",
                "description": "V3三阶段生成第1阶段：生成物理维度和社会维度的核心结构",
                "parameters": ["title", "theme", "genre", "description", "chapter_count", "narrative_perspective"]
            },
            "WORLD_BUILDING_V3_EXTENDED": {
                "name": "世界构建(V3-扩展阶段)",
                "category": "世界构建",
                "description": "V3三阶段生成第2阶段：基于核心结构扩展隐喻维度和交互维度",
                "parameters": ["core_json", "title", "theme", "genre"]
            },
            "WORLD_BUILDING_V3_FULL": {
                "name": "世界构建(V3-完整阶段)",
                "category": "世界构建",
                "description": "V3三阶段生成第3阶段：校验一致性并完善所有维度",
                "parameters": ["extended_json", "title", "theme", "genre"]
            },
            "BOOK_IMPORT_REVERSE_PROJECT_SUGGESTION": {
                "name": "拆书导入-反向项目提炼",
                "category": "拆书导入",
                "description": "基于前3章内容反向提炼简介、主题、类型、叙事视角与目标字数",
                "parameters": ["title", "sampled_text"]
            },
            "BOOK_IMPORT_REVERSE_OUTLINES": {
                "name": "拆书导入-反向章节大纲",
                "category": "拆书导入",
                "description": "基于章节正文反向生成与OUTLINE_CREATE一致结构的大纲（单批次5章）",
                "parameters": [
                    "title", "genre", "theme", "narrative_perspective",
                    "start_chapter", "end_chapter", "expected_count", "chapters_text"
                ]
            },
            "CHARACTERS_BATCH_GENERATION": {
                "name": "批量角色生成",
                "category": "角色生成",
                "description": "批量生成多个角色和组织，建立角色关系网络",
                "parameters": ["count", "world_setting", "theme", "genre", "requirements"]
            },
            "SINGLE_CHARACTER_GENERATION": {
                "name": "单个角色生成",
                "category": "角色生成",
                "description": "生成单个角色的详细设定",
                "parameters": ["project_context", "user_input"]
            },
            "SINGLE_ORGANIZATION_GENERATION": {
                "name": "组织生成",
                "category": "角色生成",
                "description": "生成组织/势力的详细设定",
                "parameters": ["project_context", "user_input"]
            },
            "OUTLINE_CREATE": {
                "name": "大纲生成",
                "category": "大纲生成",
                "description": "根据项目信息生成完整的章节大纲",
                "parameters": ["title", "theme", "genre", "chapter_count", "narrative_perspective", "target_words",
                             "world_setting", "characters_info", "requirements", "mcp_references"]
            },
            "OUTLINE_CONTINUE": {
                "name": "大纲续写",
                "category": "大纲生成",
                "description": "基于已有章节续写大纲",
                "parameters": ["title", "theme", "genre", "narrative_perspective", "chapter_count", "world_setting",
                             "characters_info", "current_chapter_count",
                             "all_chapters_brief", "recent_plot", "memory_context", "foreshadow_reminders", "mcp_references",
                             "plot_stage_instruction", "start_chapter", "end_chapter", "story_direction", "requirements"]
            },
            "CHAPTER_GENERATION_ONE_TO_MANY": {
                "name": "章节创作-1-N模式（第1章）",
                "category": "章节创作",
                "description": "1-N模式：根据大纲创作章节内容（用于第1章，无前置章节）",
                "parameters": ["project_title", "genre", "chapter_number", "chapter_title", "chapter_outline",
                             "target_word_count", "narrative_perspective", "characters_info"]
            },
            "CHAPTER_GENERATION_ONE_TO_MANY_NEXT": {
                "name": "章节创作-1-N模式（第2章及以后）",
                "category": "章节创作",
                "description": "1-N模式：基于前置章节内容创作新章节（用于第2章及以后）",
                "parameters": ["project_title", "genre", "chapter_number", "chapter_title", "chapter_outline",
                             "target_word_count", "narrative_perspective", "characters_info", "continuation_point",
                             "foreshadow_reminders", "relevant_memories", "story_skeleton", "previous_chapter_summary"]
            },
            "CHAPTER_GENERATION_ONE_TO_ONE": {
                "name": "章节创作-1-1模式（第1章）",
                "category": "章节创作",
                "description": "1-1模式：章节创作（用于第1章，无前置章节）",
                "parameters": ["project_title", "genre", "chapter_number", "chapter_title", "chapter_outline",
                             "target_word_count", "narrative_perspective", "characters_info", "chapter_careers"]
            },
            "CHAPTER_GENERATION_ONE_TO_ONE_NEXT": {
                "name": "章节创作-1-1模式（第2章及以后）",
                "category": "章节创作",
                "description": "1-1模式：基于上一章内容创作新章节（用于第2章及以后）",
                "parameters": ["project_title", "genre", "chapter_number", "chapter_title", "chapter_outline",
                             "target_word_count", "narrative_perspective", "previous_chapter_content",
                             "characters_info", "chapter_careers", "foreshadow_reminders", "relevant_memories"]
            },
            "CHAPTER_REGENERATION_SYSTEM": {
                "name": "章节重写系统提示",
                "category": "章节重写",
                "description": "用于章节重写的系统提示词",
                "parameters": ["chapter_number", "title", "word_count", "content", "modification_instructions",
                             "project_context", "style_content", "target_word_count"]
            },
            "PARTIAL_REGENERATE": {
                "name": "局部重写",
                "category": "章节重写",
                "description": "根据用户修改要求重写选中的段落内容",
                "parameters": ["context_before", "original_word_count", "selected_text", "context_after",
                             "user_instructions", "length_requirement", "style_content"]
            },
            "PLOT_ANALYSIS": {
                "name": "情节分析",
                "category": "情节分析",
                "description": "深度分析章节的剧情、钩子、伏笔等",
                "parameters": ["chapter_number", "title", "content", "word_count", "target_word_count"]
            },
            "OUTLINE_EXPAND_SINGLE": {
                "name": "大纲单批次展开",
                "category": "情节展开",
                "description": "将大纲节点展开为详细章节规划（单批次）",
                "parameters": ["project_title", "project_genre", "project_theme", "project_narrative_perspective",
                             "project_world_setting", "characters_info", "outline_order_index", "outline_title", "outline_content",
                             "context_info", "strategy_instruction", "target_chapter_count", "scene_instruction", "scene_field"]
            },
            "OUTLINE_EXPAND_MULTI": {
                "name": "大纲分批展开",
                "category": "情节展开",
                "description": "将大纲节点展开为详细章节规划（分批）",
                "parameters": ["project_title", "project_genre", "project_theme", "project_narrative_perspective",
                             "project_world_setting", "characters_info", "outline_order_index", "outline_title", "outline_content",
                             "context_info", "previous_context", "strategy_instruction", "start_index",
                             "end_index", "target_chapter_count", "scene_instruction", "scene_field"]
            },
            "MCP_TOOL_TEST": {
                "name": "MCP工具测试(用户提示词)",
                "category": "MCP测试",
                "description": "用于测试MCP插件功能的用户提示词",
                "parameters": ["plugin_name"]
            },
            "MCP_TOOL_TEST_SYSTEM": {
                "name": "MCP工具测试(系统提示词)",
                "category": "MCP测试",
                "description": "用于测试MCP插件功能的系统提示词",
                "parameters": []
            },
            "MCP_WORLD_BUILDING_PLANNING": {
                "name": "MCP世界观规划",
                "category": "MCP增强",
                "description": "使用MCP工具搜索资料辅助世界观设计",
                "parameters": ["title", "genre", "theme", "description"]
            },
            "MCP_CHARACTER_PLANNING": {
                "name": "MCP角色规划",
                "category": "MCP增强",
                "description": "使用MCP工具搜索资料辅助角色设计",
                "parameters": ["title", "genre", "theme", "time_period", "location"]
            },
            "AUTO_CHARACTER_ANALYSIS": {
                "name": "自动角色分析",
                "category": "自动角色引入",
                "description": "分析新生成的大纲，判断是否需要引入新角色",
                "parameters": ["title", "genre", "theme", "time_period", "location", "atmosphere",
                             "existing_characters", "new_outlines", "start_chapter", "end_chapter"]
            },
            "AUTO_CHARACTER_GENERATION": {
                "name": "自动角色生成",
                "category": "自动角色引入",
                "description": "根据剧情需求自动生成新角色的完整设定",
                "parameters": ["title", "genre", "theme", "world_setting",
                             "existing_characters", "plot_context", "character_specification", "mcp_references"]
            },
            "AUTO_ORGANIZATION_ANALYSIS": {
                "name": "自动组织分析",
                "category": "自动组织引入",
                "description": "分析新生成的大纲，判断是否需要引入新组织",
                "parameters": ["title", "genre", "theme", "time_period", "location", "atmosphere",
                             "existing_organizations", "existing_characters", "all_chapters_brief", "start_chapter", "chapter_count", "plot_stage", "story_direction"]
            },
            "AUTO_ORGANIZATION_GENERATION": {
                "name": "自动组织生成",
                "category": "自动组织引入",
                "description": "根据剧情需求自动生成新组织的完整设定",
                "parameters": ["title", "genre", "theme", "world_setting",
                             "existing_organizations", "existing_characters", "plot_context", "organization_specification", "mcp_references"]
            },
            "CAREER_SYSTEM_GENERATION": {
                "name": "职业体系生成",
                "category": "世界构建",
                "description": "根据世界观和项目简介自动生成完整的职业体系，包括主职业和副职业",
                "parameters": ["title", "genre", "theme", "description", "world_setting", "attribute_schema_info", "attr_example_name", "stage_example"]
            },
            "INSPIRATION_TITLE_SYSTEM": {
                "name": "灵感模式-书名生成(系统提示词)",
                "category": "灵感模式",
                "description": "根据用户的原始想法生成6个书名建议的系统提示词",
                "parameters": ["initial_idea"]
            },
            "INSPIRATION_TITLE_USER": {
                "name": "灵感模式-书名生成(用户提示词)",
                "category": "灵感模式",
                "description": "根据用户的原始想法生成6个书名建议的用户提示词",
                "parameters": ["initial_idea"]
            },
            "INSPIRATION_DESCRIPTION_SYSTEM": {
                "name": "灵感模式-简介生成(系统提示词)",
                "category": "灵感模式",
                "description": "根据用户想法和书名生成6个简介选项的系统提示词",
                "parameters": ["initial_idea", "title"]
            },
            "INSPIRATION_DESCRIPTION_USER": {
                "name": "灵感模式-简介生成(用户提示词)",
                "category": "灵感模式",
                "description": "根据用户想法和书名生成6个简介选项的用户提示词",
                "parameters": ["initial_idea", "title"]
            },
            "INSPIRATION_THEME_SYSTEM": {
                "name": "灵感模式-主题生成(系统提示词)",
                "category": "灵感模式",
                "description": "根据书名和简介生成6个深刻的主题选项的系统提示词",
                "parameters": ["initial_idea", "title", "description"]
            },
            "INSPIRATION_THEME_USER": {
                "name": "灵感模式-主题生成(用户提示词)",
                "category": "灵感模式",
                "description": "根据书名和简介生成6个深刻的主题选项的用户提示词",
                "parameters": ["initial_idea", "title", "description"]
            },
            "INSPIRATION_GENRE_SYSTEM": {
                "name": "灵感模式-类型生成(系统提示词)",
                "category": "灵感模式",
                "description": "根据小说信息生成6个合适的类型标签的系统提示词",
                "parameters": ["initial_idea", "title", "description", "theme"]
            },
            "INSPIRATION_GENRE_USER": {
                "name": "灵感模式-类型生成(用户提示词)",
                "category": "灵感模式",
                "description": "根据小说信息生成6个合适的类型标签的用户提示词",
                "parameters": ["initial_idea", "title", "description", "theme"]
            },
            "INSPIRATION_QUICK_COMPLETE": {
                "name": "灵感模式-智能补全",
                "category": "灵感模式",
                "description": "根据用户提供的部分信息智能补全完整的小说方案",
                "parameters": ["existing"]
            },
            "ITEM_ANALYSIS": {
                "name": "物品分析",
                "category": "物品管理",
                "description": "分析章节内容中的物品出现、流转和状态变化",
                "parameters": ["chapter_number", "title", "content", "existing_items", "analysis_requirements", "categories_info"]
            },
            "WORLD_BUILDING_MARKDOWN": {
                "name": "世界构建-Markdown格式",
                "category": "世界构建",
                "description": "生成Markdown格式的完整世界设定文档，涵盖物理、社会、隐喻、交互四维度及世界概述",
                "parameters": ["title", "genre", "theme", "description", "chapter_count", "narrative_perspective"]
            },
            "WORLD_BUILDING_MARKDOWN_CONTINUE": {
                "name": "世界构建-Markdown续写",
                "category": "世界构建",
                "description": "当Markdown世界设定生成因长度中断时，从中断位置续写完成剩余内容",
                "parameters": ["title", "previous_content_tail", "last_section", "missing_sections"]
            }
        }
        
        for key, info in template_definitions.items():
            template_content = getattr(cls, key, None)
            if template_content:
                templates.append({
                    "template_key": key,
                    "template_name": info["name"],
                    "category": info["category"],
                    "description": info["description"],
                    "parameters": info["parameters"],
                    "content": template_content
                })
        
        return templates
    
    @classmethod
    def get_system_template_info(cls, template_key: str) -> Optional[dict]:
        """
        获取指定系统模板的信息
        
        Args:
            template_key: 模板键名
            
        Returns:
            模板信息字典
        """
        all_templates = cls.get_all_system_templates()
        for template in all_templates:
            if template["template_key"] == template_key:
                return template
        return None

# ========== 全局实例 ==========
prompt_service = PromptService()