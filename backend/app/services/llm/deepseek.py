"""DeepSeek Provider（OpenAI 兼容 /chat/completions 流式协议）。

本实现同样适用于 OpenAI / 通义 / 月之暗面 等提供 OpenAI 兼容接口的服务商，
只需在 ai_config 里切换 base_url / model / api_key 即可。
"""
import json

import httpx

from app.services.llm.base import BaseLLMProvider
from app.utils.exceptions import BusinessException


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek 大模型接入（OpenAI chat/completions 流式协议）"""

    name = "deepseek"

    def stream_chat(self, messages, temperature=0.7, max_tokens=2048):
        yield from self._stream_chat_completions(messages, temperature, max_tokens)

    def _stream_chat_completions(self, messages, temperature, max_tokens):
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if not self.api_key:
            raise BusinessException(500, "AI 尚未配置 API Key，请联系管理员在「AI 设置」中填写")

        try:
            with httpx.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(180.0, connect=10.0),
            ) as resp:
                if resp.status_code != 200:
                    raise BusinessException(502, f"AI 服务调用失败（{resp.status_code}）：{_read_err(resp)}")

                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        yield delta
        except httpx.HTTPError as exc:
            raise BusinessException(502, f"AI 服务网络异常：{exc}")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _read_err(resp: httpx.Response) -> str:
    """读取错误响应体，截断返回，供异常信息使用。"""
    try:
        return resp.read().decode("utf-8", "ignore")[:200]
    except Exception:
        return ""
