"""世界设定Markdown处理辅助函数"""
import re
import json
from typing import Dict, List, Tuple, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.project import Project


# 必需章节列表（用于完整性检查）
REQUIRED_SECTIONS = [
    "## 基本信息",
    "## 物理维度",
    "### 空间架构",
    "### 时间架构",
    "### 力量体系",
    "### 物品体系",
    "## 社会维度",
    "### 权力结构",
    "### 经济体系",
    "### 文化体系",
    "### 组织体系",
    "## 隐喻维度",
    "## 交互维度",
    "## 世界概述",
    "### 时间背景",
    "### 地理环境",
    "### 氛围基调",
    "### 世界法则",
]

# 关键章节（至少需要这些章节才算基本完整）
KEY_SECTIONS = [
    "## 基本信息",
    "## 物理维度",
    "## 社会维度",
    "## 世界概述",
    "### 时间背景",
    "### 地理环境",
    "### 氛围基调",
    "### 世界法则",
]

# Legacy字段的多模式匹配
LEGACY_PATTERNS = {
    "time_period": [
        r"### 时间背景\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 时代背景\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 当前时代\s*\n+(.*?)(?=###|\n##|\Z)",
    ],
    "location": [
        r"### 地理环境\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 地理位置\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 地点设定\s*\n+(.*?)(?=###|\n##|\Z)",
    ],
    "atmosphere": [
        r"### 氛围基调\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 世界氛围\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 整体氛围\s*\n+(.*?)(?=###|\n##|\Z)",
    ],
    "rules": [
        r"### 世界法则\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 核心规则\s*\n+(.*?)(?=###|\n##|\Z)",
        r"### 世界规则\s*\n+(.*?)(?=###|\n##|\Z)",
    ],
}


def check_markdown_complete(markdown: str) -> Tuple[bool, List[str]]:
    """
    检查Markdown内容是否完整，返回(是否完整, 缺失章节列表)

    Args:
        markdown: Markdown文本内容

    Returns:
        Tuple[bool, List[str]]:
        - bool: 是否完整（关键章节全部存在）
        - List[str]: 缺失的章节标题列表
    """
    if not markdown:
        return False, KEY_SECTIONS.copy()

    missing = [s for s in KEY_SECTIONS if s not in markdown]
    return len(missing) == 0, missing


def check_all_sections(markdown: str) -> Tuple[bool, List[str]]:
    """
    检查所有必需章节是否完整（严格检查）

    Args:
        markdown: Markdown文本内容

    Returns:
        Tuple[bool, List[str]]:
        - bool: 是否完整（所有必需章节存在）
        - List[str]: 缺失的章节标题列表
    """
    if not markdown:
        return False, REQUIRED_SECTIONS.copy()

    missing = [s for s in REQUIRED_SECTIONS if s not in markdown]
    return len(missing) == 0, missing


def get_last_complete_section(markdown: str) -> str:
    """
    获取最后一个完整章节标题，用于续写定位

    Args:
        markdown: Markdown文本内容

    Returns:
        str: 最后一个章节标题（如 "### 权力结构"）
    """
    if not markdown:
        return ""

    lines = markdown.split('\n')
    for line in reversed(lines):
        # 匹配 ## 或 ### 开头的章节标题
        if line.startswith('##') or line.startswith('###'):
            return line.strip()

    return ""


def get_section_outline(markdown: str) -> str:
    """
    获取已完成的章节大纲摘要，用于续写时传递上下文

    Args:
        markdown: Markdown文本内容

    Returns:
        str: 章节大纲摘要（如 "已完成：基本信息、物理维度、社会维度"）
    """
    if not markdown:
        return "未开始生成"

    found_sections = []
    for section in REQUIRED_SECTIONS:
        if section in markdown:
            # 提取章节名称（去掉 ## 和 ###）
            name = section.replace('## ', '').replace('### ', '')
            found_sections.append(name)

    if found_sections:
        return f"已完成章节：{', '.join(found_sections[:10])}"
    return "未识别到已完成章节"


def extract_legacy_from_markdown(markdown: str) -> Dict[str, str]:
    """
    从Markdown中提取time_period/location/atmosphere/rules四个legacy字段

    Args:
        markdown: Markdown文本内容

    Returns:
        Dict[str, str]: 包含四个legacy字段的字典
    """
    result = {
        "time_period": "",
        "location": "",
        "atmosphere": "",
        "rules": "",
    }

    if not markdown:
        return result

    for field, patterns in LEGACY_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # 清理内容：去除多余空白、表格标记等
                content = clean_section_content(content)
                if content:
                    result[field] = content
                    break

    return result


def clean_section_content(content: str) -> str:
    """
    清理章节内容，去除Markdown标记、多余空白等

    Args:
        content: 原始章节内容

    Returns:
        str: 清理后的纯文本内容
    """
    if not content:
        return ""

    # 去除表格分隔行
    content = re.sub(r'\|[-:]+\|[-:]+\|', '', content)

    # 去除表格行中的竖线分隔，保留内容
    content = re.sub(r'\|([^|]+)\|', r'\1', content)

    # 去除多余的列表标记
    content = re.sub(r'^[-*]\s+', '', content, flags=re.MULTILINE)

    # 去除加粗标记
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)

    # 去除链接标记，保留文本
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)

    # 去除标题标记
    content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)

    # 合并多余空白
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()

    # 截取前500字（legacy字段限制）
    if len(content) > 500:
        content = content[:500].rstrip() + "..."

    return content


def clean_ai_markdown_output(raw: str) -> str:
    """
    清洗AI输出中的多余内容（解释、前言、代码块标记等）

    Args:
        raw: AI原始输出内容

    Returns:
        str: 清洗后的纯Markdown内容
    """
    if not raw:
        return ""

    # 去除开头的markdown代码块标记
    raw = re.sub(r'^```markdown\s*\n', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'^```\s*\n', '', raw)

    # 去除结尾的代码块标记
    raw = re.sub(r'\n```$', '', raw)

    # 找到第一个"# 世界观设定"并截取其后内容
    match = re.search(r'# 世界观设定', raw)
    if match:
        raw = raw[match.start():]

    # 去除AI可能添加的前言/解释
    # 常见模式："好的，以下是..."、"这是您要的世界观..."
    preamble_patterns = [
        r'^(好的|这是|以下是|根据|基于).*?\n+',
        r'^为您生成.*?\n+',
        r'^我已.*?如下.*?\n+',
    ]
    for pattern in preamble_patterns:
        raw = re.sub(pattern, '', raw, flags=re.IGNORECASE | re.DOTALL)

    return raw.strip()


def remove_duplicate_content(new_content: str, existing: str) -> str:
    """
    检测续写内容是否与已有内容重复，去除重复部分

    Args:
        new_content: 新生成的续写内容
        existing: 已有的内容

    Returns:
        str: 去除重复后的新内容
    """
    if not new_content or not existing:
        return new_content

    # 检查新内容的开头是否与已有内容的结尾重复
    # 使用滑动窗口检测重复片段（最长100字符）
    existing_lines = existing.split('\n')
    new_lines = new_content.split('\n')

    # 从后往前检查已有内容的最后几行
    for overlap_len in range(min(5, len(existing_lines)), 0, -1):
        existing_tail = '\n'.join(existing_lines[-overlap_len:])
        new_head = '\n'.join(new_lines[:overlap_len])

        if existing_tail.strip() == new_head.strip():
            # 发现重复，去除新内容的重复部分
            return '\n'.join(new_lines[overlap_len:])

    # 检查字符级别的重复（更细粒度）
    for overlap_len in range(min(100, len(existing)), 10, -10):
        existing_tail = existing[-overlap_len:]
        new_head = new_content[:overlap_len]

        if existing_tail == new_head:
            return new_content[overlap_len:]

    return new_content


def normalize_markdown_sections(markdown: str) -> str:
    """
    规范化Markdown章节结构，确保标题层级一致

    Args:
        markdown: 原始Markdown内容

    Returns:
        str: 规范化后的Markdown内容
    """
    if not markdown:
        return ""

    lines = markdown.split('\n')
    result_lines = []

    for line in lines:
        # 确保章节标题层级一致
        # 主维度使用 ## ，子维度使用 ###
        if line.startswith('# ') and not line.startswith('# 世界观设定'):
            # 主标题保持不变
            result_lines.append(line)
        elif line.startswith('## ') and '维度' in line:
            # 维度标题保持 ##
            result_lines.append(line)
        elif line.startswith('### ') and any(k in line for k in ['架构', '体系', '结构', '系统', '映射', '规则', '机制']):
            # 子维度标题保持 ###
            result_lines.append(line)
        elif line.startswith('#### '):
            # 细节标题保持 ####
            result_lines.append(line)
        else:
            result_lines.append(line)

    return '\n'.join(result_lines)


def convert_v3_json_to_markdown(data: Dict[str, Any]) -> str:
    """
    将旧V3 JSON格式转换为Markdown格式（兼容处理）

    Args:
        data: V3 JSON数据字典

    Returns:
        str: 转换后的Markdown内容
    """
    if not data:
        return ""

    lines = []
    lines.append("# 世界观设定")

    # 基本信息
    lines.append("\n## 基本信息")
    meta = data.get("meta", {})
    world_name = meta.get("world_name", "未设定")
    genre_scale = meta.get("genre_scale", "中篇")
    lines.append(f"- 世界名称：{world_name}")
    lines.append(f"- 作品规模：{genre_scale}")

    # 物理维度
    lines.append("\n## 物理维度")
    physical = data.get("physical", {})

    # 空间架构
    lines.append("\n### 空间架构")
    space = physical.get("space", {})
    if space.get("world_map"):
        lines.append("\n#### 世界地图")
        lines.append(space.get("world_map", ""))

    if space.get("key_locations"):
        lines.append("\n#### 空间节点")
        lines.append("| 名称 | 类型 | 所属区域 | 特性描述 |")
        lines.append("|------|------|----------|----------|")
        for loc in space.get("key_locations", []):
            name = loc.get("name", "未知")
            type_ = loc.get("type", "未知")
            brief = loc.get("brief", "")
            lines.append(f"| {name} | {type_} | - | {brief} |")

    if space.get("space_channels"):
        lines.append("\n#### 空间通道")
        lines.append("| 名称 | 类型 | 起点 | 终点 | 使用条件 |")
        lines.append("|------|------|------|------|----------|")
        for channel in space.get("space_channels", []):
            name = channel.get("name", "未知")
            type_ = channel.get("type", "未知")
            start = channel.get("start", "未知")
            end = channel.get("end", "未知")
            condition = channel.get("condition", "")
            lines.append(f"| {name} | {type_} | {start} | {end} | {condition} |")

    if space.get("movement_rules"):
        lines.append("\n#### 空间特性")
        lines.append(space.get("movement_rules", ""))

    # 时间架构
    lines.append("\n### 时间架构")
    time_data = physical.get("time", {})

    if time_data.get("current_period"):
        lines.append("\n#### 当前时代")
        lines.append(time_data.get("current_period", ""))

    if time_data.get("history_epochs"):
        lines.append("\n#### 历史纪元")
        lines.append("| 纪元名 | 时间跨度 | 主要影响 |")
        lines.append("|--------|----------|----------|")
        for epoch in time_data.get("history_epochs", []):
            name = epoch.get("name", "未知")
            span = epoch.get("time_span", "未知")
            impact = epoch.get("impact", "")
            lines.append(f"| {name} | {span} | {impact} |")

    if time_data.get("timeflow"):
        lines.append("\n#### 时间流速")
        lines.append(time_data.get("timeflow", ""))

    # 力量体系
    lines.append("\n### 力量体系")
    power = physical.get("power", {})

    if power.get("system_name"):
        lines.append("\n#### 力量名称")
        lines.append(f"体系名称：{power.get('system_name', '')}")

    if power.get("levels"):
        lines.append("\n#### 力量等级")
        levels = power.get("levels", [])
        if isinstance(levels, list):
            lines.append(" → ".join(levels) if levels else "未设定")

    if power.get("cultivation_method"):
        lines.append("\n#### 力量来源")
        lines.append(power.get("cultivation_method", ""))

    if power.get("level_advances"):
        lines.append("\n#### 境界突破")
        for advance in power.get("level_advances", []):
            if isinstance(advance, dict):
                level = advance.get("level", "未知")
                condition = advance.get("condition", "")
                lines.append(f"- **{level}**：{condition}")

    # 物品体系
    lines.append("\n### 物品体系")
    items = physical.get("items", {})

    if items.get("equipment_system"):
        lines.append("\n#### 装备体系")
        equip = items.get("equipment_system", {})
        if isinstance(equip, dict):
            lines.append(f"分级规则：{equip.get('grading', '未设定')}")
            lines.append(f"获取方式：{equip.get('acquisition', '未设定')}")

    if items.get("consumable_system"):
        lines.append("\n#### 消耗品体系")
        consumable = items.get("consumable_system", {})
        if isinstance(consumable, dict):
            lines.append(f"分类：{consumable.get('categories', '未设定')}")

    if items.get("rare_items"):
        lines.append("\n#### 特殊物品")
        for item in items.get("rare_items", []):
            if isinstance(item, dict):
                name = item.get("name", "未知")
                desc = item.get("description", "")
                lines.append(f"- **{name}**：{desc}")

    # 社会维度
    lines.append("\n## 社会维度")
    social = data.get("social", {})

    # 权力结构
    lines.append("\n### 权力结构")
    power_structure = social.get("power_structure", {})

    if power_structure.get("hierarchy_rule"):
        lines.append("\n#### 等级制度")
        lines.append(power_structure.get("hierarchy_rule", ""))

    if power_structure.get("key_organizations"):
        lines.append("\n#### 组织架构")
        lines.append("| 名称 | 类型 | 简介 | 实力等级 |")
        lines.append("|------|------|------|----------|")
        for org in power_structure.get("key_organizations", []):
            name = org.get("name", "未知")
            type_ = org.get("type", "未知")
            brief = org.get("brief", "")
            power_level = org.get("power_level", "未知")
            lines.append(f"| {name} | {type_} | {brief} | {power_level} |")

    if power_structure.get("power_fault_lines"):
        lines.append("\n#### 权力断层线")
        lines.append("| 名称 | 类型 | 涉及方 | 紧张程度 |")
        lines.append("|------|------|--------|----------|")
        for fault in power_structure.get("power_fault_lines", []):
            name = fault.get("name", "未知")
            type_ = fault.get("type", "未知")
            parties = fault.get("parties", "未知")
            tension = fault.get("tension", "未知")
            lines.append(f"| {name} | {type_} | {parties} | {tension} |")

    # 经济体系
    lines.append("\n### 经济体系")
    economy = social.get("economy", {})

    if economy.get("currency_system"):
        lines.append("\n#### 货币体系")
        currencies = economy.get("currency_system", [])
        if isinstance(currencies, list):
            for currency in currencies:
                if isinstance(currency, dict):
                    name = currency.get("name", "未知")
                    value = currency.get("value", "未知")
                    lines.append(f"- {name}：价值 {value}")

    if economy.get("resource_distribution"):
        lines.append("\n#### 资源分布")
        lines.append(economy.get("resource_distribution", ""))

    if economy.get("trade_networks"):
        lines.append("\n#### 贸易网络")
        lines.append("| 名称 | 类型 | 位置 | 主要商品 |")
        lines.append("|------|------|------|----------|")
        for network in economy.get("trade_networks", []):
            name = network.get("name", "未知")
            type_ = network.get("type", "未知")
            location = network.get("location", "未知")
            goods = network.get("goods", "")
            lines.append(f"| {name} | {type_} | {location} | {goods} |")

    # 文化体系
    lines.append("\n### 文化体系")
    culture = social.get("culture", {})

    if culture.get("values"):
        lines.append("\n#### 核心文化")
        for value in culture.get("values", []):
            lines.append(f"- {value}")

    if culture.get("taboos"):
        lines.append("\n#### 文化禁忌")
        for taboo in culture.get("taboos", []):
            if isinstance(taboo, dict):
                name = taboo.get("name", taboo) if isinstance(taboo, str) else taboo.get("name", "未知")
                consequence = taboo.get("consequence", "")
                lines.append(f"- **{name}**：{consequence}")

    if culture.get("traditions"):
        lines.append("\n#### 文化传承")
        for tradition in culture.get("traditions", []):
            lines.append(f"- {tradition}")

    # 组织体系
    lines.append("\n### 组织体系")
    organizations = social.get("organizations", {})

    if organizations.get("protagonist_factions"):
        lines.append("\n#### 主角阵营")
        lines.append("| 名称 | 类型 | 简介 | 实力等级 |")
        lines.append("|------|------|------|----------|")
        for faction in organizations.get("protagonist_factions", []):
            name = faction.get("name", "未知")
            type_ = faction.get("type", "未知")
            brief = faction.get("brief", "")
            power_level = faction.get("power_level", "未知")
            lines.append(f"| {name} | {type_} | {brief} | {power_level} |")

    if organizations.get("antagonist_factions"):
        lines.append("\n#### 反派阵营")
        lines.append("| 名称 | 类型 | 简介 | 实力等级 |")
        lines.append("|------|------|------|----------|")
        for faction in organizations.get("antagonist_factions", []):
            name = faction.get("name", "未知")
            type_ = faction.get("type", "未知")
            brief = faction.get("brief", "")
            power_level = faction.get("power_level", "未知")
            lines.append(f"| {name} | {type_} | {brief} | {power_level} |")

    if organizations.get("neutral_factions"):
        lines.append("\n#### 中立阵营")
        lines.append("| 名称 | 类型 | 简介 | 实力等级 |")
        lines.append("|------|------|------|----------|")
        for faction in organizations.get("neutral_factions", []):
            name = faction.get("name", "未知")
            type_ = faction.get("type", "未知")
            brief = faction.get("brief", "")
            power_level = faction.get("power_level", "未知")
            lines.append(f"| {name} | {type_} | {brief} | {power_level} |")

    # 隐喻维度
    metaphor = data.get("metaphor")
    if metaphor and isinstance(metaphor, dict):
        lines.append("\n## 隐喻维度")

        symbols = metaphor.get("symbols", {})
        if symbols:
            if symbols.get("visual"):
                lines.append("\n### 符号系统")
                lines.append("\n#### 视觉符号")
                lines.append("| 符号 | 象征意义 |")
                lines.append("|------|----------|")
                for symbol in symbols.get("visual", []):
                    name = symbol.get("symbol", symbol) if isinstance(symbol, dict) else symbol
                    meaning = symbol.get("meaning", "") if isinstance(symbol, dict) else ""
                    lines.append(f"| {name} | {meaning} |")

            if symbols.get("colors"):
                lines.append("\n#### 色彩符号")
                lines.append("| 颜色 | 含义 |")
                lines.append("|------|------|")
                for color in symbols.get("colors", []):
                    name = color.get("color", color) if isinstance(color, dict) else color
                    meaning = color.get("meaning", "") if isinstance(color, dict) else ""
                    lines.append(f"| {name} | {meaning} |")

        if metaphor.get("philosophy"):
            lines.append("\n### 哲学内核")
            for philosophy in metaphor.get("philosophy", []):
                lines.append(f"- {philosophy}")

    # 交互维度
    interaction = data.get("interaction")
    if interaction and isinstance(interaction, dict):
        lines.append("\n## 交互维度")

        cross_rules = interaction.get("cross_rules", {})
        if cross_rules:
            lines.append("\n### 维度间交互规则")
            if cross_rules.get("physical_social"):
                lines.append("\n#### 物理←→社会")
                lines.append(cross_rules.get("physical_social", ""))
            if cross_rules.get("social_metaphor"):
                lines.append("\n#### 社会←→隐喻")
                lines.append(cross_rules.get("social_metaphor", ""))

        evolution = interaction.get("evolution", {})
        if evolution:
            lines.append("\n### 动态演化机制")
            if evolution.get("time_driven"):
                lines.append("\n#### 世界观演化")
                lines.append(evolution.get("time_driven", ""))

        if interaction.get("disruption_points"):
            lines.append("\n### 破坏点与修复机制")
            lines.append("\n#### 世界观漏洞")
            for point in interaction.get("disruption_points", []):
                lines.append(f"- {point}")

    # 世界概述（legacy字段）
    lines.append("\n## 世界概述")
    legacy = data.get("legacy", {})

    lines.append("\n### 时间背景")
    time_period = legacy.get("time_period", "")
    if not time_period:
        time_period = data.get("time_period", "") or "未设定"
    lines.append(time_period)

    lines.append("\n### 地理环境")
    location = legacy.get("location", "")
    if not location:
        location = data.get("location", "") or "未设定"
    lines.append(location)

    lines.append("\n### 氛围基调")
    atmosphere = legacy.get("atmosphere", "")
    if not atmosphere:
        atmosphere = data.get("atmosphere", "") or "未设定"
    lines.append(atmosphere)

    lines.append("\n### 世界法则")
    rules = legacy.get("rules", "")
    if not rules:
        rules = data.get("rules", "") or "未设定"
    lines.append(rules)

    return '\n'.join(lines)


def get_world_setting_content(project: "Project") -> str:
    """
    统一返回Markdown格式的世界设定内容，兼容旧JSON数据

    Args:
        project: 项目模型实例

    Returns:
        str: Markdown格式的世界设定内容
    """
    # 优先使用Markdown格式
    if project.world_setting_format == 'markdown' and project.world_setting_markdown:
        return project.world_setting_markdown

    # 兼容旧JSON格式
    if project.world_setting_data:
        try:
            data = json.loads(project.world_setting_data)
            return convert_v3_json_to_markdown(data)
        except json.JSONDecodeError:
            pass

    # 最降级：使用legacy 4字段拼接简单内容
    parts = ["# 世界观设定\n\n## 世界概述"]
    if project.world_time_period:
        parts.append(f"\n### 时间背景\n{project.world_time_period}")
    if project.world_location:
        parts.append(f"\n### 地理环境\n{project.world_location}")
    if project.world_atmosphere:
        parts.append(f"\n### 氛围基调\n{project.world_atmosphere}")
    if project.world_rules:
        parts.append(f"\n### 世界法则\n{project.world_rules}")

    return '\n'.join(parts)


def build_enriched_context_from_markdown(markdown: str) -> Dict[str, Any]:
    """
    从Markdown提取丰富的世界观上下文，供其他生成流程使用

    Args:
        markdown: Markdown格式的世界设定

    Returns:
        Dict包含：
        - legacy 4字段
        - key_organizations: 势力列表
        - key_locations: 地点列表
        - power_levels: 力量等级列表
    """
    result = extract_legacy_from_markdown(markdown)

    # 提取势力信息（从组织体系表格）
    result["key_organizations"] = extract_organizations_from_markdown(markdown)

    # 提取地点信息（从空间节点表格）
    result["key_locations"] = extract_locations_from_markdown(markdown)

    # 提取力量等级（从力量等级章节）
    result["power_levels"] = extract_power_levels_from_markdown(markdown)

    return result


def extract_organizations_from_markdown(markdown: str) -> List[Dict[str, str]]:
    """
    从Markdown中提取势力/组织信息

    Args:
        markdown: Markdown内容

    Returns:
        List[Dict]: 势力列表，每个包含name, type, brief
    """
    organizations = []

    # 匹配组织表格
    patterns = [
        r"#### 主角阵营\s*\n+\|.*?\n\|[-:]+\|[-:]+\|[-:]+\|[-:]+\|\n([\s\S]*?)(?=####|\n###|\n##|\Z)",
        r"#### 反派阵营\s*\n+\|.*?\n\|[-:]+\|[-:]+\|[-:]+\|[-:]+\|\n([\s\S]*?)(?=####|\n###|\n##|\Z)",
        r"#### 中立阵营\s*\n+\|.*?\n\|[-:]+\|[-:]+\|[-:]+\|[-:]+\|\n([\s\S]*?)(?=####|\n###|\n##|\Z)",
        r"#### 组织架构\s*\n+\|.*?\n\|[-:]+\|[-:]+\|[-:]+\|[-:]+\|\n([\s\S]*?)(?=####|\n###|\n##|\Z)",
    ]

    for pattern in patterns:
        match = re.search(pattern, markdown, re.DOTALL)
        if match:
            table_content = match.group(1)
            # 解析表格行
            rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|', table_content)
            for row in rows:
                name = row[0].strip()
                type_ = row[1].strip()
                brief = row[2].strip()
                if name and name not in ['名称', '------']:
                    organizations.append({
                        "name": name,
                        "type": type_,
                        "brief": brief
                    })

    return organizations


def extract_locations_from_markdown(markdown: str) -> List[Dict[str, str]]:
    """
    从Markdown中提取地点信息

    Args:
        markdown: Markdown内容

    Returns:
        List[Dict]: 地点列表，每个包含name, type, brief
    """
    locations = []

    # 匹配空间节点表格
    pattern = r"#### 空间节点\s*\n+\|.*?\n\|[-:]+\|[-:]+\|[-:]+\|[-:]+\|\n([\s\S]*?)(?=####|\n###|\n##|\Z)"
    match = re.search(pattern, markdown, re.DOTALL)
    if match:
        table_content = match.group(1)
        rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|', table_content)
        for row in rows:
            name = row[0].strip()
            type_ = row[1].strip()
            region = row[2].strip()
            brief = row[3].strip()
            if name and name not in ['名称', '------']:
                locations.append({
                    "name": name,
                    "type": type_,
                    "region": region,
                    "brief": brief
                })

    return locations


def extract_power_levels_from_markdown(markdown: str) -> List[str]:
    """
    从Markdown中提取力量等级列表

    Args:
        markdown: Markdown内容

    Returns:
        List[str]: 力量等级名称列表
    """
    levels = []

    # 匹配力量等级章节
    pattern = r"#### 力量等级\s*\n+([^\n]+)"
    match = re.search(pattern, markdown)
    if match:
        content = match.group(1).strip()
        # 解析 "等级1 → 等级2 → 等级3" 格式
        if '→' in content:
            levels = [l.strip() for l in content.split('→') if l.strip()]
        # 解析列表格式
        elif content.startswith('-'):
            levels = [l.strip().lstrip('-') for l in content.split('\n') if l.strip().startswith('-')]
        else:
            levels = [content]

    return levels