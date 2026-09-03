"""LLM Provider 抽象基类（V1.4.8）：统一 stream_chat 接口，多模型可扩展。

新增一个模型供应商只需：继承 BaseLLMProvider 实现 stream_chat，
再到 services/llm/__init__.py 的 get_provider 工厂里注册路由即可，
业务层（ai_service / router）无需任何改动。
"""
from abc import ABC, abstractmethod
from typing import Iterator


class BaseLLMProvider(ABC):
    """LLM 供应商抽象基类。

    统一输出契约：stream_chat 逐段 yield 增量文本片段（str），
    由上层负责拼装与 SSE 转发。
    """

    name = "base"

    def __init__(self, model: str, api_key: str, base_url: str, **kwargs):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """流式对话，逐段 yield 增量文本。"""
        raise NotImplementedError
