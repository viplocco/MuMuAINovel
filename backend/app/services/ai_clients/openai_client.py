"""OpenAI 客户端"""
import json
from typing import Any, AsyncGenerator, Dict, Optional

from app.logger import get_logger
from .base_client import BaseAIClient

logger = get_logger(__name__)


class OpenAIClient(BaseAIClient):
    """OpenAI API 客户端"""

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stream:
            payload["stream"] = True
        if tools:
            # 清理 $schema 字段
            cleaned = []
            for t in tools:
                tc = t.copy()
                if "function" in tc and "parameters" in tc["function"]:
                    tc["function"]["parameters"] = {
                        k: v for k, v in tc["function"]["parameters"].items() if k != "$schema"
                    }
                cleaned.append(tc)
            payload["tools"] = cleaned
            if tool_choice:
                payload["tool_choice"] = tool_choice
        return payload

    async def chat_completion(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = self._build_payload(messages, model, temperature, max_tokens, tools, tool_choice)

        logger.info(f"📤 OpenAI 请求 - 模型: {model}, max_tokens: {max_tokens}, 温度: {temperature}")
        logger.debug(f"📤 OpenAI 请求 payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:1000]}...")

        data = await self._request_with_retry("POST", "/chat/completions", payload)

        # 调试日志：输出原始响应
        logger.info(f"📥 OpenAI 原始响应键: {data.keys() if isinstance(data, dict) else type(data)}")

        # 详细记录响应内容
        if isinstance(data, dict):
            usage = data.get('usage', {})
            if usage:
                logger.info(f"📥 Token使用 - prompt: {usage.get('prompt_tokens')}, completion: {usage.get('completion_tokens')}, total: {usage.get('total_tokens')}")

        choices = data.get("choices", [])
        if not choices or len(choices) == 0:
            logger.error(f"❌ API 返回空 choices: {data}")
            raise ValueError("API 返回空 choices 或 choices 为空列表")

        choice = choices[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason")
        content = message.get("content", "")

        logger.info(f"📥 响应详情 - finish_reason: {finish_reason}, content长度: {len(content) if content else 0}")

        # 如果content为空但finish_reason是length，记录警告
        if not content and finish_reason == 'length':
            logger.warning(f"⚠️ 智谱AI返回空内容但finish_reason为length，这可能是模型配置问题")
            logger.warning(f"📥 完整choice: {choice}")

        return {
            "content": content,
            "tool_calls": message.get("tool_calls"),
            "finish_reason": finish_reason,
        }

    async def chat_completion_stream(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成，支持工具调用

        Yields:
            Dict with keys:
            - content: str - 文本内容块
            - tool_calls: list - 工具调用列表（如果有）
            - done: bool - 是否结束
        """
        payload = self._build_payload(messages, model, temperature, max_tokens, tools, tool_choice, stream=True)

        logger.info(f"📤 OpenAI 流式请求 - 模型: {model}, max_tokens: {max_tokens}, 温度: {temperature}")
        logger.info(f"📤 流式请求 payload 预览: messages数量={len(messages)}, 总字符数={sum(len(str(m.get('content', ''))) for m in messages)}")
        # 记录 messages 内容预览
        for i, msg in enumerate(messages[:2]):  # 只显示前2条
            content_preview = str(msg.get('content', ''))[:300]
            logger.info(f"📤 messages[{i}] role={msg.get('role')}: {content_preview}...")
        logger.debug(f"📤 完整 payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:2000]}...")

        tool_calls_buffer = {}  # 收集工具调用块
        finish_reason = None  # 记录结束原因

        try:
            async with await self._request_with_retry("POST", "/chat/completions", payload, stream=True) as response:
                # 检查响应状态码和headers
                logger.info(f"📥 流式响应状态码: {response.status_code}")
                logger.info(f"📥 流式响应headers: {dict(response.headers)}")
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"❌ 流式响应非200状态: {response.status_code}, body: {error_body[:500]}")
                    raise ValueError(f"API返回非200状态码: {response.status_code}")

                response.raise_for_status()
                chunk_count = 0
                content_count = 0
                raw_line_count = 0  # 统计原始行数
                first_line_content = None  # 记录第一行内容
                buffer = ""  # 用于手动解析的缓冲区

                try:
                    # 首先尝试使用 aiter_bytes() 更稳健地处理流
                    incomplete_bytes = b''  # 用于保存不完整的 UTF-8 字节
                    consecutive_failures = 0  # 连续解码失败计数
                    MAX_CONSECUTIVE_FAILURES = 3  # 最大连续失败次数，超过后清空 incomplete_bytes

                    async for chunk_bytes in response.aiter_bytes():
                        chunk_text = None

                        # 策略1：先尝试单独解码新 chunk（很多情况下 chunk 本身是完整的）
                        try:
                            chunk_text = chunk_bytes.decode('utf-8')
                            # 新 chunk 单独解码成功，说明 incomplete_bytes 是孤立数据（上一个流结束了）
                            if incomplete_bytes:
                                logger.debug(f"   新chunk独立解码成功，丢弃{len(incomplete_bytes)}字节孤立数据")
                                incomplete_bytes = b''
                            consecutive_failures = 0
                        except UnicodeDecodeError:
                            # 新 chunk 单独解码失败，尝试与 incomplete_bytes 合并
                            combined_bytes = incomplete_bytes + chunk_bytes

                            try:
                                chunk_text = combined_bytes.decode('utf-8')
                                # 合并解码成功，清空 incomplete_bytes
                                incomplete_bytes = b''
                                consecutive_failures = 0
                            except UnicodeDecodeError as ude:
                                consecutive_failures += 1
                                logger.warning(f"⚠️ UTF-8解码失败(连续{consecutive_failures}次): {ude}")

                                # 策略2：使用 replace 模式解码，避免完全丢弃数据
                                # 这会将无效字节替换为  符号
                                chunk_text = combined_bytes.decode('utf-8', errors='replace')

                                # 检查是否有末尾不完整的多字节字符
                                # 如果连续失败次数过多，清空 incomplete_bytes
                                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                    logger.warning(f"   连续解码失败{consecutive_failures}次，清空遗留字节")
                                    incomplete_bytes = b''
                                    consecutive_failures = 0
                                else:
                                    # 尝试保存末尾可能的 UTF-8 不完整字节（最多4字节）
                                    # 检查末尾是否有 UTF-8 多字节起始字节
                                    for i in range(min(4, len(combined_bytes))):
                                        last_byte = combined_bytes[-(i+1)]
                                        # UTF-8 多字节起始字节范围
                                        if 0xC0 <= last_byte <= 0xDF:  # 2字节起始
                                            incomplete_bytes = combined_bytes[-(i+1):]
                                            break
                                        elif 0xE0 <= last_byte <= 0xEF:  # 3字节起始（中文）
                                            incomplete_bytes = combined_bytes[-(i+1):]
                                            break
                                        elif 0xF0 <= last_byte <= 0xF7:  # 4字节起始
                                            incomplete_bytes = combined_bytes[-(i+1):]
                                            break
                                    else:
                                        # 没找到起始字节，清空
                                        incomplete_bytes = b''

                                    if incomplete_bytes:
                                        # 从 chunk_text 中移除对应的替换符号（因为这些字节等待下次合并）
                                        # Unicode 替换字符是 U+FFFD
                                        num_replacement_chars = len(incomplete_bytes) // 3 if len(incomplete_bytes) >= 3 else 0
                                        if num_replacement_chars > 0 and chunk_text.endswith('\ufffd' * num_replacement_chars):
                                            chunk_text = chunk_text[:-num_replacement_chars]
                                        logger.debug(f"   保留{len(incomplete_bytes)}字节等待下次合并")

                        if chunk_text:
                            buffer += chunk_text

                        # 按换行符分割处理
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            raw_line_count += 1

                            # 记录第一行原始内容
                            if raw_line_count == 1:
                                first_line_content = line[:500]
                                logger.info(f"📥 流式第1行原始内容(bytes解码): {first_line_content}")

                            # 处理行内容
                            if not line.startswith("data: "):
                                if line.strip():
                                    logger.info(f"📥 流式行[{raw_line_count}]不以data:开头: {line[:200]}")
                                    try:
                                        error_data = json.loads(line)
                                        if "error" in error_data:
                                            error_msg = error_data.get("error", {})
                                            logger.error(f"❌ API返回错误: {error_msg}")
                                            raise ValueError(f"API错误: {error_msg.get('message', str(error_msg))}")
                                    except json.JSONDecodeError:
                                        pass
                                continue

                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                logger.info(f"📥 OpenAI 流式结束 - 原始行数: {raw_line_count}, 收到 {chunk_count} 个chunk, {content_count} 个有效内容块, finish_reason: {finish_reason}")
                                if tool_calls_buffer:
                                    yield {"tool_calls": list(tool_calls_buffer.values()), "done": True, "finish_reason": finish_reason}
                                yield {"done": True, "finish_reason": finish_reason}
                                break

                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices and len(choices) > 0:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    chunk_count += 1

                                    fr = choices[0].get("finish_reason")
                                    if fr:
                                        finish_reason = fr

                                    tc_list = delta.get("tool_calls")
                                    if tc_list:
                                        for tc in tc_list:
                                            index = tc.get("index", 0)
                                            if index not in tool_calls_buffer:
                                                tool_calls_buffer[index] = tc
                                            else:
                                                existing = tool_calls_buffer[index]
                                                if "function" in tc and "function" in existing:
                                                    if tc["function"].get("arguments"):
                                                        existing["function"]["arguments"] = (
                                                            existing["function"].get("arguments", "") +
                                                            tc["function"]["arguments"]
                                                        )

                                    if content:
                                        content_count += 1
                                        yield {"content": content}

                            except json.JSONDecodeError:
                                logger.debug(f"JSON解析失败: {data_str[:100]}")
                                continue

                    # 流结束后，处理 buffer 中可能遗留的内容
                    if buffer.strip():
                        logger.warning(f"⚠️ 流结束后buffer仍有内容: {buffer[:200]}")

                    # 处理可能遗留的不完整字节
                    if incomplete_bytes:
                        logger.warning(f"⚠️ 流结束后仍有{len(incomplete_bytes)}字节未解码数据")

                except GeneratorExit:
                    # 生成器被关闭，这是正常的清理过程
                    logger.debug("流式响应生成器被关闭(GeneratorExit)")
                    raise
                except UnicodeDecodeError as ude:
                    # UTF-8 解码错误，尝试返回已接收的内容
                    logger.error(f"流式响应UTF-8解码错误: {ude}")
                    if buffer.strip():
                        logger.warning(f"⚠️ 返回已接收的部分内容: {len(buffer)}字符")
                        # 尝试处理 buffer 中已有的内容
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            if line.startswith("data: ") and not line.strip().endswith("[DONE]"):
                                data_str = line[6:]
                                try:
                                    data = json.loads(data_str)
                                    choices = data.get("choices", [])
                                    if choices and len(choices) > 0:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield {"content": content}
                                except json.JSONDecodeError:
                                    pass
                    yield {"done": True, "finish_reason": "error", "error": str(ude)}
                except Exception as iter_error:
                    logger.error(f"流式响应迭代出错: {str(iter_error)}")
                    # 返回已接收的内容
                    if buffer.strip():
                        logger.warning(f"⚠️ 返回已接收的部分内容: {len(buffer)}字符")
                    yield {"done": True, "finish_reason": "error", "error": str(iter_error)}
        except GeneratorExit:
            # 重新抛出GeneratorExit，让调用方处理
            raise
        except Exception as e:
            logger.error(f"流式请求出错: {str(e)}")
            raise