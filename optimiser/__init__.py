"""
Headroom - The Context Optimization Layer for LLM Applications.

Cut your LLM costs by 50-90% without losing accuracy.

Headroom wraps LLM clients to provide:
- Smart compression of tool outputs (keeps errors, anomalies, relevant items)
- Cache-aligned prefix optimization for better provider cache hits
- Rolling window token management for long conversations
- Full streaming support with zero accuracy loss

Quick Start:

    from optimiser import HeadroomClient, OpenAIProvider
    from openai import OpenAI

    # Wrap your existing client
    client = HeadroomClient(
        original_client=OpenAI(),
        provider=OpenAIProvider(),
        default_mode="optimize",
    )

    # Use exactly like the original client
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Hello!"},
        ],
    )

    # Check savings
    stats = client.get_stats()
    print(f"Tokens saved: {stats['session']['tokens_saved_total']}")

Verify It's Working:

    # Validate configuration
    result = client.validate_setup()
    if not result["valid"]:
        print("Issues:", result)

    # Enable logging to see what's happening
    import logging
    logging.basicConfig(level=logging.INFO)
    # INFO:headroom.transforms.pipeline:Pipeline complete: 45000 -> 4500 tokens

Simulate Before Sending:

    plan = client.chat.completions.simulate(
        model="gpt-4o",
        messages=large_messages,
    )
    print(f"Would save {plan.tokens_saved} tokens")
    print(f"Transforms: {plan.transforms}")

Error Handling:

    from optimiser import HeadroomError, ConfigurationError, ProviderError

    try:
        response = client.chat.completions.create(...)
    except ConfigurationError as e:
        print(f"Config issue: {e.details}")
    except HeadroomError as e:
        print(f"Headroom error: {e}")

For more examples, see https://github.com/headroom-sdk/headroom/tree/main/examples
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from ._version import __version__  # noqa: F401
from .compress import CompressConfig, CompressResult, compress, compress_spreadsheet

# Keep a real callable bound for the one-function compression API so
# `from optimiser import compress` is never shadowed by the submodule object.

__all__ = [
    # Main client
    "HeadroomClient",
    # Providers
    "Provider",
    "TokenCounter",
    "OpenAIProvider",
    "AnthropicProvider",
    # Exceptions
    "HeadroomError",
    "ConfigurationError",
    "ProviderError",
    "StorageError",
    "CompressionError",
    "TokenizationError",
    "CacheError",
    "ValidationError",
    "TransformError",
    # Config
    "HeadroomConfig",
    "HeadroomMode",
    "SmartCrusherConfig",
    "CacheAlignerConfig",
    "CacheOptimizerConfig",
    "RelevanceScorerConfig",
    # Data models
    "Block",
    "CachePrefixMetrics",
    "DiffArtifact",
    "RequestMetrics",
    "SimulationResult",
    "TransformDiff",
    "TransformResult",
    "WasteSignals",
    # Transforms
    "SmartCrusher",
    "CacheAligner",
    "TransformPipeline",
    # Cache optimizers
    "BaseCacheOptimizer",
    "CacheConfig",
    "CacheMetrics",
    "CacheResult",
    "CacheStrategy",
    "OptimizationContext",
    "CacheOptimizerRegistry",
    "AnthropicCacheOptimizer",
    "OpenAICacheOptimizer",
    "GoogleCacheOptimizer",
    "SemanticCache",
    "SemanticCacheLayer",
    # Relevance scoring - BM25 always available, embeddings require sentence-transformers
    "RelevanceScore",
    "RelevanceScorer",
    "BM25Scorer",
    "EmbeddingScorer",
    "HybridScorer",
    "create_scorer",
    "embedding_available",
    # Utilities
    "Tokenizer",
    "count_tokens_text",
    "count_tokens_messages",
    "generate_report",
    # Observability
    "HeadroomOtelMetrics",
    "HeadroomTracer",
    "LangfuseTracingConfig",
    "OTelMetricsConfig",
    "configure_otel_metrics",
    "configure_langfuse_tracing",
    "get_headroom_tracer",
    "get_langfuse_tracing_status",
    "get_otel_metrics",
    "get_otel_metrics_status",
    "reset_headroom_tracing",
    "reset_otel_metrics",
    # Memory - optional hierarchical memory system
    "with_memory",  # Main user-facing API
    "Memory",
    "ScopeLevel",
    "HierarchicalMemory",
    "MemoryConfig",
    "EmbedderBackend",
    # One-function compression API
    "compress",
    "compress_spreadsheet",
    "CompressConfig",
    "CompressResult",
    # Hooks
    "CompressionHooks",
    "CompressContext",
    "CompressEvent",
    # Canonical pipeline
    "PipelineStage",
    "PipelineEvent",
    "PipelineExtensionManager",
    "CANONICAL_PIPELINE_STAGES",
    # Shared context for multi-agent workflows
    "SharedContext",
]

# Keep package-level imports lightweight so `import headroom` does not eagerly
# load provider SDKs, ML stacks, or optional proxy/runtime integrations.
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Main client
    "HeadroomClient": ("optimiser.client", "HeadroomClient"),
    # Providers
    "Provider": ("optimiser.providers", "Provider"),
    "TokenCounter": ("optimiser.providers", "TokenCounter"),
    "OpenAIProvider": ("optimiser.providers", "OpenAIProvider"),
    "AnthropicProvider": ("optimiser.providers", "AnthropicProvider"),
    # Exceptions
    "HeadroomError": ("optimiser.exceptions", "HeadroomError"),
    "ConfigurationError": ("optimiser.exceptions", "ConfigurationError"),
    "ProviderError": ("optimiser.exceptions", "ProviderError"),
    "StorageError": ("optimiser.exceptions", "StorageError"),
    "CompressionError": ("optimiser.exceptions", "CompressionError"),
    "TokenizationError": ("optimiser.exceptions", "TokenizationError"),
    "CacheError": ("optimiser.exceptions", "CacheError"),
    "ValidationError": ("optimiser.exceptions", "ValidationError"),
    "TransformError": ("optimiser.exceptions", "TransformError"),
    # Config
    "HeadroomConfig": ("optimiser.config", "HeadroomConfig"),
    "HeadroomMode": ("optimiser.config", "HeadroomMode"),
    "SmartCrusherConfig": ("optimiser.config", "SmartCrusherConfig"),
    "CacheAlignerConfig": ("optimiser.config", "CacheAlignerConfig"),
    "CacheOptimizerConfig": ("optimiser.config", "CacheOptimizerConfig"),
    "RelevanceScorerConfig": ("optimiser.config", "RelevanceScorerConfig"),
    # Data models
    "Block": ("optimiser.config", "Block"),
    "CachePrefixMetrics": ("optimiser.config", "CachePrefixMetrics"),
    "DiffArtifact": ("optimiser.config", "DiffArtifact"),
    "RequestMetrics": ("optimiser.config", "RequestMetrics"),
    "SimulationResult": ("optimiser.config", "SimulationResult"),
    "TransformDiff": ("optimiser.config", "TransformDiff"),
    "TransformResult": ("optimiser.config", "TransformResult"),
    "WasteSignals": ("optimiser.config", "WasteSignals"),
    # Transforms
    "SmartCrusher": ("optimiser.transforms", "SmartCrusher"),
    "CacheAligner": ("optimiser.transforms", "CacheAligner"),
    "TransformPipeline": ("optimiser.transforms", "TransformPipeline"),
    # Cache optimizers
    "BaseCacheOptimizer": ("optimiser.cache", "BaseCacheOptimizer"),
    "CacheConfig": ("optimiser.cache", "CacheConfig"),
    "CacheMetrics": ("optimiser.cache", "CacheMetrics"),
    "CacheResult": ("optimiser.cache", "CacheResult"),
    "CacheStrategy": ("optimiser.cache", "CacheStrategy"),
    "OptimizationContext": ("optimiser.cache", "OptimizationContext"),
    "CacheOptimizerRegistry": ("optimiser.cache", "CacheOptimizerRegistry"),
    "AnthropicCacheOptimizer": ("optimiser.cache", "AnthropicCacheOptimizer"),
    "OpenAICacheOptimizer": ("optimiser.cache", "OpenAICacheOptimizer"),
    "GoogleCacheOptimizer": ("optimiser.cache", "GoogleCacheOptimizer"),
    "SemanticCache": ("optimiser.cache", "SemanticCache"),
    "SemanticCacheLayer": ("optimiser.cache", "SemanticCacheLayer"),
    # Relevance scoring
    "RelevanceScore": ("optimiser.relevance", "RelevanceScore"),
    "RelevanceScorer": ("optimiser.relevance", "RelevanceScorer"),
    "BM25Scorer": ("optimiser.relevance", "BM25Scorer"),
    "EmbeddingScorer": ("optimiser.relevance", "EmbeddingScorer"),
    "HybridScorer": ("optimiser.relevance", "HybridScorer"),
    "create_scorer": ("optimiser.relevance", "create_scorer"),
    "embedding_available": ("optimiser.relevance", "embedding_available"),
    # Utilities
    "Tokenizer": ("optimiser.tokenizer", "Tokenizer"),
    "count_tokens_text": ("optimiser.tokenizer", "count_tokens_text"),
    "count_tokens_messages": ("optimiser.tokenizer", "count_tokens_messages"),
    "generate_report": ("optimiser.reporting", "generate_report"),
    # Observability
    "HeadroomOtelMetrics": ("optimiser.observability", "HeadroomOtelMetrics"),
    "HeadroomTracer": ("optimiser.observability", "HeadroomTracer"),
    "LangfuseTracingConfig": ("optimiser.observability", "LangfuseTracingConfig"),
    "OTelMetricsConfig": ("optimiser.observability", "OTelMetricsConfig"),
    "configure_otel_metrics": ("optimiser.observability", "configure_otel_metrics"),
    "configure_langfuse_tracing": ("optimiser.observability", "configure_langfuse_tracing"),
    "get_headroom_tracer": ("optimiser.observability", "get_headroom_tracer"),
    "get_langfuse_tracing_status": ("optimiser.observability", "get_langfuse_tracing_status"),
    "get_otel_metrics": ("optimiser.observability", "get_otel_metrics"),
    "get_otel_metrics_status": ("optimiser.observability", "get_otel_metrics_status"),
    "reset_headroom_tracing": ("optimiser.observability", "reset_headroom_tracing"),
    "reset_otel_metrics": ("optimiser.observability", "reset_otel_metrics"),
    # One-function API
    "compress": ("optimiser.compress", "compress"),
    "compress_spreadsheet": ("optimiser.compress", "compress_spreadsheet"),
    # Hooks
    "CompressionHooks": ("optimiser.hooks", "CompressionHooks"),
    "CompressContext": ("optimiser.hooks", "CompressContext"),
    "CompressEvent": ("optimiser.hooks", "CompressEvent"),
    # Canonical pipeline
    "PipelineStage": ("optimiser.pipeline", "PipelineStage"),
    "PipelineEvent": ("optimiser.pipeline", "PipelineEvent"),
    "PipelineExtensionManager": ("optimiser.pipeline", "PipelineExtensionManager"),
    "CANONICAL_PIPELINE_STAGES": ("optimiser.pipeline", "CANONICAL_PIPELINE_STAGES"),
    # Shared context
    "SharedContext": ("optimiser.shared_context", "SharedContext"),
}

# Memory remains optional and preserves the long-standing behavior of exposing
# `None` when the extra dependencies are not installed.
_OPTIONAL_EXPORTS = {
    "with_memory": ("optimiser.memory", "with_memory"),
    "Memory": ("optimiser.memory", "Memory"),
    "ScopeLevel": ("optimiser.memory", "ScopeLevel"),
    "HierarchicalMemory": ("optimiser.memory", "HierarchicalMemory"),
    "MemoryConfig": ("optimiser.memory", "MemoryConfig"),
    "EmbedderBackend": ("optimiser.memory", "EmbedderBackend"),
}


def __getattr__(name: str) -> Any:
    """Resolve package exports lazily while preserving legacy import paths."""
    module_attr = _LAZY_EXPORTS.get(name)
    if module_attr is not None:
        module_name, attr_name = module_attr
        value = getattr(import_module(module_name), attr_name)
        globals()[name] = value
        return value

    optional_module_attr = _OPTIONAL_EXPORTS.get(name)
    if optional_module_attr is not None:
        module_name, attr_name = optional_module_attr
        try:
            value = getattr(import_module(module_name), attr_name)
        except ImportError:
            value = None
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
