"""修复 DeepSeek 兼容性问题"""
import re

with open('app/api/chapters.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到并替换生成参数部分
old_code = '''# 准备生成参数
                generate_kwargs = {
                    "prompt": prompt,
                    "system_prompt": system_prompt_with_style,
                    "max_tokens": calculated_max_tokens  # 添加 max_tokens 限制
                }
                
                # 只有 OpenAI 原生 API 支持 tool_choice 参数
                # DeepSeek 等兼容 API 不支持此参数
                if custom_model and not custom_model.startswith("deepseek"):
                    generate_kwargs["tool_choice"] = "required"
                
                if custom_model:
                    logger.info(f"  使用自定义模型：{custom_model}")
                    generate_kwargs["model"] = custom_model'''

new_code = '''# 准备生成参数
                generate_kwargs = {
                    "prompt": prompt,
                    "system_prompt": system_prompt_with_style,
                    "max_tokens": calculated_max_tokens,
                    "auto_mcp": True
                }
                
                # DeepSeek 等兼容 API 不支持 tools 和 tool_choice 参数
                if custom_model and custom_model.startswith("deepseek"):
                    generate_kwargs["auto_mcp"] = False
                    logger.info(f"  DeepSeek 模型，已禁用 MCP 工具和 tool_choice")
                elif custom_model:
                    generate_kwargs["tool_choice"] = "required"
                
                if custom_model:
                    logger.info(f"  使用自定义模型：{custom_model}")
                    generate_kwargs["model"] = custom_model'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('app/api/chapters.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ 修改成功')
else:
    print('❌ 未找到匹配的代码')
    print('查找的代码片段:')
    print(repr(old_code[:100]))
