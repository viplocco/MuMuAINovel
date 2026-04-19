"""JSON 处理工具类"""
import json
import re
from typing import Any, Dict, List, Optional, Union
from app.logger import get_logger

logger = get_logger(__name__)

# JSON 中有效的转义字符（反斜杠后可跟的字符）
VALID_ESCAPE_CHARS = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}


def _normalize_json_quotes(text: str) -> str:
    """
    规范化 JSON 中的中文引号为英文引号

    只处理看起来像 JSON 键值对的引号，避免误替换小说正文中的对话引号

    中文引号：左引号 \u201c ("), 右引号 \u201d (")
    """
    if not text:
        return text

    # 中文引号的 Unicode 字符
    LEFT_QUOTE = '\u201c'  # "
    RIGHT_QUOTE = '\u201d'  # "

    # 模式1：中文引号后跟英文冒号（键名） -> 替换为英文引号
    # 如："name": -> "name":
    text = re.sub(r'[' + LEFT_QUOTE + RIGHT_QUOTE + r']([^' + LEFT_QUOTE + RIGHT_QUOTE + r']+)[' + LEFT_QUOTE + RIGHT_QUOTE + r']\s*:', r'"\\1":', text)

    # 模式2：英文冒号后中文引号（值） -> 替换为英文引号
    # 如：: "value" -> : "value"
    text = re.sub(r':\s*[' + LEFT_QUOTE + RIGHT_QUOTE + r']([^' + LEFT_QUOTE + RIGHT_QUOTE + r']*)[' + LEFT_QUOTE + RIGHT_QUOTE + r']', r': "\\1"', text)

    # 模式3：中文引号作为数组元素 -> 替换为英文引号
    # 如：["item"] -> ["item"]
    text = re.sub(r'\[\s*[' + LEFT_QUOTE + RIGHT_QUOTE + r']([^' + LEFT_QUOTE + RIGHT_QUOTE + r']*)[' + LEFT_QUOTE + RIGHT_QUOTE + r']', r'[ "\\1"', text)
    text = re.sub(r'[' + LEFT_QUOTE + RIGHT_QUOTE + r']([^' + LEFT_QUOTE + RIGHT_QUOTE + r']*)[' + LEFT_QUOTE + RIGHT_QUOTE + r']\s*\]', r'"\\1" ]', text)

    return text


def clean_json_response(text: str) -> str:
    """清洗 AI 返回的 JSON（改进版 - 流式安全 + 控制字符处理）"""
    try:
        if not text:
            logger.warning("⚠️ clean_json_response: 输入为空")
            return text

        original_length = len(text)
        logger.debug(f"🔍 开始清洗JSON，原始长度: {original_length}")

        # 去除 markdown 代码块
        text = re.sub(r'^```json\s*\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^```\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()

        if len(text) != original_length:
            logger.debug(f"   移除markdown后长度: {len(text)}")

        # 规范化中文引号
        normalized_text = _normalize_json_quotes(text)
        if normalized_text != text:
            logger.debug(f"   规范化引号后有变化")
            text = normalized_text

        # 尝试直接解析（快速路径）
        try:
            json.loads(text)
            logger.debug(f"✅ 直接解析成功，无需清洗")
            return text
        except json.JSONDecodeError as e:
            # 如果是控制字符错误，尝试修复
            if "Invalid control character" in str(e):
                logger.debug(f"   检测到控制字符问题，尝试修复...")
                text = _fix_control_characters(text)
                try:
                    json.loads(text)
                    logger.debug(f"✅ 控制字符修复后解析成功")
                    return text
                except:
                    pass
            # 如果是无效转义错误，尝试修复
            if "Invalid \\escape" in str(e) or "Invalid escape" in str(e):
                logger.debug(f"   检测到无效转义序列，尝试修复...")
                text = _fix_invalid_escapes(text)
                try:
                    json.loads(text)
                    logger.debug(f"✅ 无效转义修复后解析成功")
                    return text
                except:
                    pass

        # 找到第一个 { 或 [
        start = -1
        for i, c in enumerate(text):
            if c in ('{', '['):
                start = i
                break

        if start == -1:
            logger.warning(f"⚠️ 未找到JSON起始符号 {{ 或 [")
            logger.debug(f"   文本预览: {text[:200]}")
            return text

        if start > 0:
            logger.debug(f"   跳过前{start}个字符")
            text = text[start:]

        # 改进的括号匹配算法（更严格的字符串处理）
        stack = []
        i = 0
        end = -1
        in_string = False

        while i < len(text):
            c = text[i]

            # 处理字符串状态
            if c == '"':
                if not in_string:
                    # 进入字符串
                    in_string = True
                else:
                    # 检查是否是转义的引号
                    num_backslashes = 0
                    j = i - 1
                    while j >= 0 and text[j] == '\\':
                        num_backslashes += 1
                        j -= 1

                    # 偶数个反斜杠表示引号未被转义，字符串结束
                    if num_backslashes % 2 == 0:
                        in_string = False

                i += 1
                continue

            # 在字符串内部，跳过所有字符
            if in_string:
                i += 1
                continue

            # 处理括号（只有在字符串外部才有效）
            if c == '{' or c == '[':
                stack.append(c)
            elif c == '}':
                if len(stack) > 0 and stack[-1] == '{':
                    stack.pop()
                    if len(stack) == 0:
                        end = i + 1
                        logger.debug(f"✅ 找到JSON结束位置: {end}")
                        break
                elif len(stack) > 0:
                    # 括号不匹配，可能是损坏的JSON，尝试继续
                    logger.warning(f"⚠️ 括号不匹配：遇到 }} 但栈顶是 {stack[-1]}")
                else:
                    # 栈为空遇到 }，忽略多余的闭合括号
                    logger.warning(f"⚠️ 遇到多余的 }}，忽略")
            elif c == ']':
                if len(stack) > 0 and stack[-1] == '[':
                    stack.pop()
                    if len(stack) == 0:
                        end = i + 1
                        logger.debug(f"✅ 找到JSON结束位置: {end}")
                        break
                elif len(stack) > 0:
                    # 括号不匹配，可能是损坏的JSON，尝试继续
                    logger.warning(f"⚠️ 括号不匹配：遇到 ] 但栈顶是 {stack[-1]}")
                else:
                    # 栈为空遇到 ]，忽略多余的闭合括号
                    logger.warning(f"⚠️ 遇到多余的 ]，忽略")

            i += 1

        # 检查未闭合的字符串
        if in_string:
            logger.warning(f"⚠️ 字符串未闭合，JSON可能不完整")

        # 提取结果
        if end > 0:
            result = text[:end]
            logger.debug(f"✅ JSON清洗完成，结果长度: {len(result)}")
        else:
            result = text
            logger.warning(f"⚠️ 未找到JSON结束位置，返回全部内容（长度: {len(result)}）")
            logger.debug(f"   栈状态: {stack}")

        # 尝试修复控制字符
        result = _fix_control_characters(result)

        # 尝试修复无效转义序列
        result = _fix_invalid_escapes(result)

        # 尝试修复截断的 JSON（闭合未闭合的字符串和括号）
        try:
            json.loads(result)
            logger.debug(f"✅ JSON验证成功")
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON验证失败: {e}，尝试截断修复...")
            result = _fix_truncated_json(result)

        # 最终验证
        try:
            json.loads(result)
            logger.debug(f"✅ 最终JSON验证成功")
        except json.JSONDecodeError as e:
            logger.error(f"❌ 最终JSON仍然无效: {e}")
            logger.debug(f"   结果预览: {result[:500]}")
            logger.debug(f"   结果结尾: ...{result[-200:]}")

        return result

    except Exception as e:
        logger.error(f"❌ clean_json_response 出错: {e}")
        logger.error(f"   文本长度: {len(text) if text else 0}")
        logger.error(f"   文本预览: {text[:200] if text else 'None'}")
        raise


def _fix_truncated_json(text: str) -> str:
    """
    修复截断的 JSON：闭合未闭合的字符串和括号

    常见截断模式：
    1. 字符串未闭合（"content... 截断）
    2. 数组/对象未闭合（[{... 截断）
    3. 字段值截断（"key": "value... 截断）
    """
    if not text:
        return text

    # 先检查是否已经是有效 JSON
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    result = []
    stack = []  # 括号栈：记录 { 或 [
    in_string = False
    last_key = None
    i = 0
    truncated_string_start = -1

    while i < len(text):
        c = text[i]

        # 处理字符串边界
        if c == '"' and not in_string:
            in_string = True
            truncated_string_start = i
            result.append(c)
            i += 1
            continue
        elif c == '"':
            # 检查是否是转义的引号
            num_backslashes = 0
            j = i - 1
            while j >= 0 and text[j] == '\\':
                num_backslashes += 1
                j -= 1

            if num_backslashes % 2 == 0:
                in_string = False
                truncated_string_start = -1
            result.append(c)
            i += 1
            continue

        # 在字符串内部
        if in_string:
            # 处理反斜杠（可能需要转义）
            if c == '\\':
                # 检查后面是否有字符
                if i + 1 < len(text):
                    next_char = text[i + 1]
                    # 如果是有效转义，保留原样
                    if next_char in VALID_ESCAPE_CHARS:
                        result.append('\\')
                        result.append(next_char)
                        i += 2
                        continue
                    else:
                        # 无效转义，修复为双反斜杠
                        result.append('\\')
                        result.append('\\')
                        result.append(next_char)
                        i += 2
                        continue
                else:
                    # 末尾孤立反斜杠
                    result.append('\\')
                    result.append('\\')
                    i += 1
                    continue

            # 检查是否是控制字符（需要转义）
            if ord(c) < 32:
                # 转义控制字符
                if c == '\n':
                    result.append('\\n')
                elif c == '\r':
                    result.append('\\r')
                elif c == '\t':
                    result.append('\\t')
                elif c == '\b':
                    result.append('\\b')
                elif c == '\f':
                    result.append('\\f')
                else:
                    result.append(f'\\u{ord(c):04x}')
            else:
                result.append(c)
            i += 1
            continue

        # 处理括号（字符串外部）
        if c == '{':
            stack.append('{')
            result.append(c)
        elif c == '[':
            stack.append('[')
            result.append(c)
        elif c == '}':
            if stack and stack[-1] == '{':
                stack.pop()
            result.append(c)
        elif c == ']':
            if stack and stack[-1] == '[':
                stack.pop()
            result.append(c)
        elif c == ':':
            # 记录键名（用于判断截断位置）
            last_key = ''.join(result).rsplit('"', 2)[-1].strip('"') if '"' in ''.join(result)[-50:] else None
            result.append(c)
        elif c == ',':
            result.append(c)
        else:
            result.append(c)

        i += 1

    # 处理截断：闭合未闭合的字符串
    if in_string:
        logger.warning(f"⚠️ 字符串未闭合，位置: {truncated_string_start}")
        # 添加截断标记并闭合字符串
        result.append('...[截断]"')
        in_string = False

    # 处理截断：闭合未闭合的括号
    if stack:
        logger.warning(f"⚠️ 括栈未闭合: {stack}")

        # 根据栈内容判断需要添加什么
        while stack:
            bracket = stack.pop()
            if bracket == '{':
                # 对象未闭合，可能需要添加 null 或闭合
                # 检查最后一个字符是否是 : 或 ,
                last_chars = ''.join(result).rstrip()[-10:]
                if last_chars.rstrip().endswith(':'):
                    # 字段值缺失，补 null
                    result.append('null')
                elif last_chars.rstrip().endswith(','):
                    # 多余逗号，移除
                    while result and result[-1] in (' ', ',', '\n', '\t'):
                        result.pop()
                result.append('}')
            elif bracket == '[':
                # 数组未闭合
                last_chars = ''.join(result).rstrip()[-10:]
                if last_chars.rstrip().endswith(','):
                    # 多余逗号，移除
                    while result and result[-1] in (' ', ',', '\n', '\t'):
                        result.pop()
                result.append(']')

    fixed = ''.join(result)
    logger.debug(f"   修复后长度: {len(fixed)}")

    # 验证修复结果
    try:
        json.loads(fixed)
        logger.info(f"✅ 截断 JSON 修复成功")
        return fixed
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ 修复后仍无效: {e}")
        return fixed  # 返回修复尝试，让上层处理


def _fix_control_characters(text: str) -> str:
    """
    修复 JSON 字符串值中的控制字符

    JSON 规范要求字符串值中的控制字符必须被转义。
    此函数在字符串值内部将未转义的控制字符转义。
    """
    result = []
    i = 0
    in_string = False

    while i < len(text):
        c = text[i]

        # 处理字符串边界
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                # 检查是否是转义的引号
                num_backslashes = 0
                j = i - 1
                while j >= 0 and text[j] == '\\':
                    num_backslashes += 1
                    j -= 1

                if num_backslashes % 2 == 0:
                    in_string = False
                result.append(c)
            i += 1
            continue

        # 在字符串内部处理控制字符
        if in_string:
            # 检查是否是控制字符（ASCII 0-31，除了已转义的）
            if ord(c) < 32:
                # 检查前面是否有转义符
                num_backslashes = 0
                j = len(result) - 1
                while j >= 0 and result[j] == '\\':
                    num_backslashes += 1
                    j -= 1

                # 如果前面没有转义符（或偶数个转义符），则需要转义
                if num_backslashes % 2 == 0:
                    # 转义控制字符
                    if c == '\n':
                        result.append('\\n')
                    elif c == '\r':
                        result.append('\\r')
                    elif c == '\t':
                        result.append('\\t')
                    elif c == '\b':
                        result.append('\\b')
                    elif c == '\f':
                        result.append('\\f')
                    else:
                        # 其他控制字符，用 \\uXXXX 表示
                        result.append(f'\\u{ord(c):04x}')
                    i += 1
                    continue

            result.append(c)
            i += 1
            continue

        # 在字符串外部，保留所有字符
        result.append(c)
        i += 1

    return ''.join(result)


def _fix_invalid_escapes(text: str) -> str:
    r"""
    修复 JSON 字符串值中的无效转义序列

    JSON 规范要求反斜杠后必须跟有效的转义字符：
    \" \\ \/ \b \f \n \r \t \uXXXX

    如果出现无效转义（如 \x \a \c 等），将其修复为 \\ 或直接移除反斜杠。
    这是 DeepSeek 等模型返回 JSON 时常见的问题。
    """
    result = []
    i = 0
    in_string = False

    while i < len(text):
        c = text[i]

        # 处理字符串边界
        if c == '"':
            # 检查是否是转义的引号
            num_backslashes = 0
            j = i - 1
            while j >= 0 and result[j] == '\\':
                num_backslashes += 1
                j -= 1

            # 如果引号前有奇数个反斜杠，它是转义的，字符串状态不变
            if num_backslashes % 2 == 1:
                result.append(c)
                i += 1
                continue

            # 否则切换字符串状态
            in_string = not in_string
            result.append(c)
            i += 1
            continue

        # 在字符串内部处理反斜杠
        if in_string and c == '\\':
            # 检查后面是否有字符
            if i + 1 < len(text):
                next_char = text[i + 1]

                # 检查是否是有效的转义序列
                if next_char in VALID_ESCAPE_CHARS:
                    # 有效转义，保留原样
                    result.append(c)
                    result.append(next_char)
                    i += 2
                    continue
                else:
                    # 无效转义，将 \ 替换为 \\（转义反斜杠本身）
                    logger.debug(f"   修复无效转义: \\{next_char} -> \\\\{next_char} (位置 {i})")
                    result.append('\\')
                    result.append('\\')
                    result.append(next_char)
                    i += 2
                    continue
            else:
                # 字符串末尾的孤立反斜杠，移除或转义
                logger.debug(f"   修复末尾孤立反斜杠 (位置 {i})")
                result.append('\\')
                result.append('\\')
                i += 1
                continue

        # 其他字符正常处理
        result.append(c)
        i += 1

    return ''.join(result)


def parse_json(text: str, fallback: Union[Dict, List, None] = None) -> Union[Dict, List]:
    """
    解析 JSON，支持降级返回默认值

    Args:
        text: 待解析的 JSON 文本
        fallback: 解析失败时的降级返回值，默认抛出异常

    Returns:
        解析后的 Dict 或 List，或 fallback 值

    Raises:
        JSONDecodeError: 当解析失败且未提供 fallback 时
    """
    try:
        cleaned = clean_json_response(text)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析失败: {e}")
        logger.error(f"   原始文本长度: {len(text) if text else 0}")
        logger.error(f"   错误位置: 行 {e.lineno}, 列 {e.colno}")

        # 提取错误附近的上下文
        if text and e.pos:
            start = max(0, e.pos - 50)
            end = min(len(text), e.pos + 50)
            logger.error(f"   错误上下文: ...{text[start:end]}...")

        if fallback is not None:
            logger.warning(f"⚠️ 使用降级数据: {type(fallback).__name__}")
            return fallback
        raise
    except Exception as e:
        logger.error(f"❌ parse_json 出错: {e}")
        logger.error(f"   原始文本长度: {len(text) if text else 0}")

        if fallback is not None:
            logger.warning(f"⚠️ 使用降级数据: {type(fallback).__name__}")
            return fallback
        raise


def safe_parse_json_v3_world_setting(text: str) -> Dict:
    """
    安全解析 V3 世界设定 JSON，提供智能降级

    当 JSON 解析失败时，尝试从残缺数据中提取有效字段，
    并填充默认结构。

    Args:
        text: 待解析的 JSON 文本

    Returns:
        V3 世界设定结构（至少包含 version=2 和 legacy 字段）
    """
    # 默认降级结构（完整字段 - 与 V3_COMPLETE_STRUCTURE 同步）
    default_structure = {
        "version": 2,
        "meta": {
            "world_name": "",
            "genre_scale": "中篇",
            "creation_stage": "core"
        },
        "physical": {
            "space": {
                "world_map": None,
                "key_locations": [],
                "space_nodes": [],
                "space_channels": [],
                "space_features": [],
                "movement_rules": ""
            },
            "time": {
                "current_period": "",
                "history_epochs": [],
                "history_events": [],
                "time_nodes": [],
                "timeflow": ""
            },
            "power": {
                "system_name": "",
                "levels": [],
                "cultivation_method": "",
                "limitations": "",
                "ability_branches": [],
                "power_sources": [],
                "level_advances": []
            },
            "items": {
                "equipment_system": None,
                "consumable_system": None,
                "tool_system": None,
                "structure_system": None,
                "creature_system": None,
                "rare_items": [],
                "common_items": [],
                "creation_rules": ""
            }
        },
        "social": {
            "power_structure": {
                "hierarchy_rule": "",
                "key_organizations": [],
                "faction_classification": [],
                "power_fault_lines": [],
                "power_balance": [],
                "conflict_rules": ""
            },
            "economy": {
                "currency_system": [],
                "trade_rules": "",
                "resource_distribution": "",
                "trade_networks": [],
                "economic_lifelines": []
            },
            "culture": {
                "values": [],
                "taboos": [],
                "traditions": [],
                "language_style": "",
                "core_culture": [],
                "religious_beliefs": [],
                "cultural_heritage": []
            },
            "organizations": {
                "protagonist_factions": [],
                "antagonist_factions": [],
                "neutral_factions": [],
                "special_factions": []
            },
            "relations": {
                "organization_relations": [],
                "inter_personal_rules": ""
            }
        },
        # 默认设为空对象结构而非None，便于后续合并
        "metaphor": {
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
            "core_philosophies": [],
            "philosophy": []
        },
        "interaction": {
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
        },
        "legacy": {
            "time_period": "未设定",
            "location": "未设定",
            "atmosphere": "未设定",
            "rules": "未设定"
        }
    }

    if not text:
        logger.warning("⚠️ 输入为空，返回默认结构")
        return default_structure

    try:
        cleaned = clean_json_response(text)
        data = json.loads(cleaned)

        # 验证必要字段
        if "version" not in data:
            logger.warning("⚠️ 缺少 version 字段，设为 2")
            data["version"] = 2

        if "legacy" not in data:
            logger.warning("⚠️ 缺少 legacy 字段，尝试从文本提取")

            # 尝试从残缺数据中提取 legacy 字段
            legacy = _extract_legacy_from_partial(text, data)
            data["legacy"] = legacy

        # 补充缺失的维度
        if "physical" not in data:
            data["physical"] = default_structure["physical"]
        if "social" not in data:
            data["social"] = default_structure["social"]
        if "meta" not in data:
            data["meta"] = default_structure["meta"]

        # 补充物理维度缺失的子字段
        physical = data.get("physical", {})
        if "space" not in physical:
            physical["space"] = {"key_locations": []}
        if "time" not in physical:
            physical["time"] = {"current_period": ""}
        if "power" not in physical:
            physical["power"] = {"system_name": "", "levels": [], "cultivation_method": ""}
        else:
            power = physical.get("power", {})
            if "cultivation_method" not in power:
                power["cultivation_method"] = ""
            if "levels" not in power:
                power["levels"] = []
        if "items" not in physical:
            physical["items"] = {"rare_items": []}
        data["physical"] = physical

        # 补充社会维度缺失的子字段
        social = data.get("social", {})
        if "power_structure" not in social:
            social["power_structure"] = {"hierarchy_rule": "", "key_organizations": []}
        else:
            power_structure = social.get("power_structure", {})
            if "hierarchy_rule" not in power_structure:
                power_structure["hierarchy_rule"] = ""
            if "key_organizations" not in power_structure:
                power_structure["key_organizations"] = []
            social["power_structure"] = power_structure
        if "culture" not in social:
            social["culture"] = {"values": [], "taboos": []}
        else:
            culture = social.get("culture", {})
            if "values" not in culture:
                culture["values"] = []
            if "taboos" not in culture:
                culture["taboos"] = []
            social["culture"] = culture
        data["social"] = social

        return data

    except json.JSONDecodeError as e:
        logger.error(f"❌ V3 世界设定解析失败: {e}")

        # 尝试从残缺 JSON 中提取有价值的信息
        extracted = _extract_partial_world_setting(text)

        if extracted:
            logger.info(f"✅ 从残缺数据中提取了部分内容")
            # 合入默认结构
            for key in ["meta", "physical", "social", "legacy"]:
                if key in extracted:
                    default_structure[key] = extracted[key]
            return default_structure

        return default_structure


def _extract_legacy_from_partial(text: str, data: Dict) -> Dict:
    """
    从部分解析的 JSON 或原始文本中提取 legacy 字段
    """
    legacy = {
        "time_period": "未设定",
        "location": "未设定",
        "atmosphere": "未设定",
        "rules": "未设定"
    }

    # 从已解析的 data 中查找
    if "time_period" in data:
        legacy["time_period"] = data["time_period"]
    if "location" in data:
        legacy["location"] = data["location"]
    if "atmosphere" in data:
        legacy["atmosphere"] = data["atmosphere"]
    if "rules" in data:
        legacy["rules"] = data["rules"]

    # 从原始文本中正则提取
    patterns = {
        "time_period": r'"time_period"\s*:\s*"([^"]*)"',
        "location": r'"location"\s*:\s*"([^"]*)"',
        "atmosphere": r'"atmosphere"\s*:\s*"([^"]*)"',
        "rules": r'"rules"\s*:\s*"([^"]*)"'
    }

    for key, pattern in patterns.items():
        if legacy[key] == "未设定":
            match = re.search(pattern, text)
            if match:
                legacy[key] = match.group(1)

    return legacy


def _extract_partial_world_setting(text: str) -> Optional[Dict]:
    """
    从残缺的 JSON 文本中尽可能提取有效内容
    """
    result = {}

    # 提取 meta
    world_name_match = re.search(r'"world_name"\s*:\s*"([^"]*)"', text)
    if world_name_match:
        result["meta"] = {
            "world_name": world_name_match.group(1),
            "genre_scale": "中篇",
            "creation_stage": "core"
        }

    # 提取 key_locations
    locations = []
    loc_pattern = r'"name"\s*:\s*"([^"]*)"\s*,\s*"type"\s*:\s*"([^"]*)"\s*,\s*"brief"\s*:\s*"([^"]*)"'
    for match in re.finditer(loc_pattern, text):
        # 限制提取数量，避免误匹配
        if len(locations) < 10:
            locations.append({
                "name": match.group(1),
                "type": match.group(2),
                "brief": match.group(3)
            })
    if locations:
        result["physical"] = {"space": {"key_locations": locations}}

    # 提取 key_organizations
    organizations = []
    org_pattern = r'"name"\s*:\s*"([^"]*)"\s*,\s*"type"\s*:\s*"([^"]*)"\s*,\s*"brief"\s*:\s*"([^"]*)"'
    # 需要区分 locations 和 organizations，通过上下文判断
    if "key_organizations" in text:
        org_section = text[text.find("key_organizations"):]
        org_section = org_section[:org_section.find("]") + 1] if "]" in org_section else org_section[:500]
        for match in re.finditer(org_pattern, org_section):
            if len(organizations) < 10:
                organizations.append({
                    "name": match.group(1),
                    "type": match.group(2),
                    "brief": match.group(3)
                })
    if organizations:
        result["social"] = {"power_structure": {"key_organizations": organizations}}

    # 提取 legacy 字段
    legacy = _extract_legacy_from_partial(text, {})
    if any(v != "未设定" for v in legacy.values()):
        result["legacy"] = legacy

    return result if result else None