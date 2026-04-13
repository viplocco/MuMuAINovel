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
        logger.debug(f"📤 流式请求 messages 数量: {len(messages)}, 总字符数: {sum(len(m.get('content', '')) for m in messages)}")

        tool_calls_buffer = {}  # 收集工具调用块
        finish_reason = None  # 记录结束原因

        try:
            async with await self._request_with_retry("POST", "/chat/completions", payload, stream=True) as response:
                # 检查响应状态码
                logger.info(f"📥 流式响应状态码: {response.status_code}")
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"❌ 流式响应非200状态: {response.status_code}, body: {error_body[:500]}")
                    raise ValueError(f"API返回非200状态码: {response.status_code}")

                response.raise_for_status()
                chunk_count = 0
                content_count = 0
                raw_line_count = 0  # 统计原始行数
                try:
                    async for line in response.aiter_lines():
                        raw_line_count += 1
                        # 记录前几行原始内容以便诊断
                        if raw_line_count <= 3:
                            logger.debug(f"📥 流式原始行[{raw_line_count}]: {line[:200]}")

                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                # 流结束，检查是否有工具调用需要处理
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

                                    # 提取 finish_reason（在流的最后几个 chunk 中出现）
                                    fr = choices[0].get("finish_reason")
                                    if fr:
                                        finish_reason = fr

                                    # 检查工具调用
                                    tc_list = delta.get("tool_calls")
                                    if tc_list:
                                        for tc in tc_list:
                                            index = tc.get("index", 0)
                                            if index not in tool_calls_buffer:
                                                tool_calls_buffer[index] = tc
                                            else:
                                                existing = tool_calls_buffer[index]
                                                # 合并 function.arguments
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
                                continue
                except GeneratorExit:
                    # 生成器被关闭，这是正常的清理过程
                    logger.debug("流式响应生成器被关闭(GeneratorExit)")
                    raise
                except Exception as iter_error:
                    logger.error(f"流式响应迭代出错: {str(iter_error)}")
                    raise
        except GeneratorExit:
            # 重新抛出GeneratorExit，让调用方处理
            raise
        except Exception as e:
            logger.error(f"流式请求出错: {str(e)}")
            raise