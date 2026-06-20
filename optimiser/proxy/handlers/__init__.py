"""Handler mixins for HeadroomProxy.

Each mixin class contains methods extracted from HeadroomProxy that handle
requests for a specific provider or concern. The mixins rely on HeadroomProxy's
__init__ for all self.* attributes (duck typing).
"""

from optimiser.proxy.handlers.anthropic import AnthropicHandlerMixin
from optimiser.proxy.handlers.batch import BatchHandlerMixin
from optimiser.proxy.handlers.bedrock import BedrockHandlerMixin
from optimiser.proxy.handlers.gemini import GeminiHandlerMixin
from optimiser.proxy.handlers.openai import OpenAIHandlerMixin
from optimiser.proxy.handlers.streaming import StreamingMixin

__all__ = [
    "AnthropicHandlerMixin",
    "BatchHandlerMixin",
    "BedrockHandlerMixin",
    "GeminiHandlerMixin",
    "OpenAIHandlerMixin",
    "StreamingMixin",
]
