"""LLM Provider 层统一入口：抽象基类 + DeepSeek 实现 + 工厂函数"""
from app.services.llm.base import BaseLLMProvider
from app.services.llm.deepseek import DeepSeekProvider

__all__ = ["BaseLLMProvider", "DeepSeekProvider", "get_provider"]


def get_provider(config) -> BaseLLMProvider:
    """根据 ai_config 返回对应 Provider（V1.4.8：DeepSeek 为首个实现）。

    DeepSeekProvider 基于 OpenAI chat/completions 流式协议，天然兼容
    OpenAI / 通义 / 月之暗面 等 OpenAI 兼容接口；未来接入非 OpenAI 协议的
    模型（如 Claude）时，新增 Provider 类并在此按 base_url（或新增 provider
    字段）路由即可，业务层无需改动。
    """
    return DeepSeekProvider(
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )
