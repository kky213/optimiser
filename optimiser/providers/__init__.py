"""Provider abstractions for Headroom SDK.

Providers encapsulate model-specific behavior like tokenization,
context limits, and cost estimation.

Supported Providers:
- OpenAIProvider: Native OpenAI models (GPT-4o, o1, etc.)
- AnthropicProvider: Claude models
- GoogleProvider: Google Gemini models
- CohereProvider: Cohere Command models
- OpenAICompatibleProvider: Universal provider for any OpenAI-compatible API
  (Ollama, vLLM, Together, Groq, Fireworks, LM Studio, etc.)
- LiteLLMProvider: Universal provider via LiteLLM (100+ providers)
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Expose concrete types to static analysis while keeping runtime imports lazy.
    from optimiser.providers.anthropic import AnthropicProvider
    from optimiser.providers.base import Provider, TokenCounter
    from optimiser.providers.cohere import CohereProvider
    from optimiser.providers.google import GoogleProvider
    from optimiser.providers.litellm import (
        LiteLLMProvider,
        create_litellm_provider,
        is_litellm_available,
    )
    from optimiser.providers.openai import OpenAIProvider
    from optimiser.providers.openai_compatible import (
        ModelCapabilities,
        OpenAICompatibleProvider,
        create_anyscale_provider,
        create_fireworks_provider,
        create_groq_provider,
        create_lmstudio_provider,
        create_ollama_provider,
        create_together_provider,
        create_vllm_provider,
    )

__all__ = [
    # Base
    "Provider",
    "TokenCounter",
    # Native providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "CohereProvider",
    # Universal providers
    "OpenAICompatibleProvider",
    "ModelCapabilities",
    "LiteLLMProvider",
    "is_litellm_available",
    # Factory functions
    "create_ollama_provider",
    "create_together_provider",
    "create_groq_provider",
    "create_fireworks_provider",
    "create_anyscale_provider",
    "create_vllm_provider",
    "create_lmstudio_provider",
    "create_litellm_provider",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Base
    "Provider": ("optimiser.providers.base", "Provider"),
    "TokenCounter": ("optimiser.providers.base", "TokenCounter"),
    # Native providers
    "OpenAIProvider": ("optimiser.providers.openai", "OpenAIProvider"),
    "AnthropicProvider": ("optimiser.providers.anthropic", "AnthropicProvider"),
    "GoogleProvider": ("optimiser.providers.google", "GoogleProvider"),
    "CohereProvider": ("optimiser.providers.cohere", "CohereProvider"),
    # Universal providers
    "OpenAICompatibleProvider": (
        "optimiser.providers.openai_compatible",
        "OpenAICompatibleProvider",
    ),
    "ModelCapabilities": ("optimiser.providers.openai_compatible", "ModelCapabilities"),
    "LiteLLMProvider": ("optimiser.providers.litellm", "LiteLLMProvider"),
    "is_litellm_available": ("optimiser.providers.litellm", "is_litellm_available"),
    # Factory functions
    "create_ollama_provider": ("optimiser.providers.openai_compatible", "create_ollama_provider"),
    "create_together_provider": (
        "optimiser.providers.openai_compatible",
        "create_together_provider",
    ),
    "create_groq_provider": ("optimiser.providers.openai_compatible", "create_groq_provider"),
    "create_fireworks_provider": (
        "optimiser.providers.openai_compatible",
        "create_fireworks_provider",
    ),
    "create_anyscale_provider": (
        "optimiser.providers.openai_compatible",
        "create_anyscale_provider",
    ),
    "create_vllm_provider": ("optimiser.providers.openai_compatible", "create_vllm_provider"),
    "create_lmstudio_provider": (
        "optimiser.providers.openai_compatible",
        "create_lmstudio_provider",
    ),
    "create_litellm_provider": ("optimiser.providers.litellm", "create_litellm_provider"),
}


def __getattr__(name: str) -> object:
    if name == "__path__":
        raise AttributeError(name)

    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
