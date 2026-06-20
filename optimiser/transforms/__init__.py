"""Transform modules for Headroom SDK."""

from __future__ import annotations

import importlib.util
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Expose concrete types to static analysis while keeping runtime imports lazy.
    from optimiser.transforms.anchor_selector import (  # noqa: F401
        AnchorSelector,
        AnchorStrategy,
        AnchorWeights,
        DataPattern,
        calculate_information_score,
        compute_item_hash,
    )
    from optimiser.transforms.base import Transform  # noqa: F401
    from optimiser.transforms.cache_aligner import CacheAligner  # noqa: F401
    from optimiser.transforms.code_compressor import (  # noqa: F401
        CodeAwareCompressor,
        CodeCompressionResult,
        CodeCompressorConfig,
        CodeLanguage,
        DocstringMode,
        detect_language,
        is_tree_sitter_available,
    )
    from optimiser.transforms.content_detector import (  # noqa: F401
        ContentType,
        DetectionResult,
        detect_content_type,
    )
    from optimiser.transforms.content_router import (  # noqa: F401
        CompressionStrategy,
        ContentRouter,
        ContentRouterConfig,
        RouterCompressionResult,
    )
    from optimiser.transforms.diff_compressor import (  # noqa: F401
        DiffCompressionResult,
        DiffCompressor,
        DiffCompressorConfig,
    )
    from optimiser.transforms.html_extractor import (  # noqa: F401
        HTMLExtractionResult,
        HTMLExtractor,
        HTMLExtractorConfig,
        is_html_content,
    )
    from optimiser.transforms.log_compressor import (  # noqa: F401
        LogCompressionResult,
        LogCompressor,
        LogCompressorConfig,
    )
    from optimiser.transforms.pipeline import TransformPipeline  # noqa: F401
    from optimiser.transforms.search_compressor import (  # noqa: F401
        SearchCompressionResult,
        SearchCompressor,
        SearchCompressorConfig,
    )
    from optimiser.transforms.smart_crusher import SmartCrusher, SmartCrusherConfig  # noqa: F401
    from optimiser.transforms.tabular_ingest import (  # noqa: F401
        TabularCompressionResult,
        TabularCompressor,
        TabularCompressorConfig,
    )

_HTML_EXTRACTOR_AVAILABLE = importlib.util.find_spec("trafilatura") is not None

__all__ = [
    # Base
    "Transform",
    "TransformPipeline",
    # Anchor selection
    "AnchorSelector",
    "AnchorStrategy",
    "AnchorWeights",
    "DataPattern",
    "calculate_information_score",
    "compute_item_hash",
    # JSON compression
    "SmartCrusher",
    "SmartCrusherConfig",
    # Text compression (coding tasks)
    "ContentType",
    "DetectionResult",
    "detect_content_type",
    "SearchCompressor",
    "SearchCompressorConfig",
    "SearchCompressionResult",
    "LogCompressor",
    "LogCompressorConfig",
    "LogCompressionResult",
    "TabularCompressor",
    "TabularCompressorConfig",
    "TabularCompressionResult",
    "DiffCompressor",
    "DiffCompressorConfig",
    "DiffCompressionResult",
    # Code-aware compression (AST-based)
    "CodeAwareCompressor",
    "CodeCompressorConfig",
    "CodeCompressionResult",
    "CodeLanguage",
    "DocstringMode",
    "detect_language",
    "is_tree_sitter_available",
    # Content routing
    "ContentRouter",
    "ContentRouterConfig",
    "RouterCompressionResult",
    "CompressionStrategy",
    # Other transforms
    "CacheAligner",
    # HTML extraction (optional)
    "_HTML_EXTRACTOR_AVAILABLE",
]

# Conditionally add HTML extractor exports
if _HTML_EXTRACTOR_AVAILABLE:
    __all__.extend(
        [
            "HTMLExtractor",
            "HTMLExtractorConfig",
            "HTMLExtractionResult",
            "is_html_content",
        ]
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # Base
    "Transform": ("optimiser.transforms.base", "Transform"),
    "TransformPipeline": ("optimiser.transforms.pipeline", "TransformPipeline"),
    # Anchor selection
    "AnchorSelector": ("optimiser.transforms.anchor_selector", "AnchorSelector"),
    "AnchorStrategy": ("optimiser.transforms.anchor_selector", "AnchorStrategy"),
    "AnchorWeights": ("optimiser.transforms.anchor_selector", "AnchorWeights"),
    "DataPattern": ("optimiser.transforms.anchor_selector", "DataPattern"),
    "calculate_information_score": (
        "optimiser.transforms.anchor_selector",
        "calculate_information_score",
    ),
    "compute_item_hash": ("optimiser.transforms.anchor_selector", "compute_item_hash"),
    # JSON compression
    "SmartCrusher": ("optimiser.transforms.smart_crusher", "SmartCrusher"),
    "SmartCrusherConfig": ("optimiser.transforms.smart_crusher", "SmartCrusherConfig"),
    # Text compression (coding tasks)
    "ContentType": ("optimiser.transforms.content_detector", "ContentType"),
    "DetectionResult": ("optimiser.transforms.content_detector", "DetectionResult"),
    "detect_content_type": ("optimiser.transforms.content_detector", "detect_content_type"),
    "SearchCompressor": ("optimiser.transforms.search_compressor", "SearchCompressor"),
    "SearchCompressorConfig": (
        "optimiser.transforms.search_compressor",
        "SearchCompressorConfig",
    ),
    "SearchCompressionResult": (
        "optimiser.transforms.search_compressor",
        "SearchCompressionResult",
    ),
    "LogCompressor": ("optimiser.transforms.log_compressor", "LogCompressor"),
    "LogCompressorConfig": ("optimiser.transforms.log_compressor", "LogCompressorConfig"),
    "LogCompressionResult": ("optimiser.transforms.log_compressor", "LogCompressionResult"),
    "TabularCompressor": ("optimiser.transforms.tabular_ingest", "TabularCompressor"),
    "TabularCompressorConfig": (
        "optimiser.transforms.tabular_ingest",
        "TabularCompressorConfig",
    ),
    "TabularCompressionResult": (
        "optimiser.transforms.tabular_ingest",
        "TabularCompressionResult",
    ),
    "DiffCompressor": ("optimiser.transforms.diff_compressor", "DiffCompressor"),
    "DiffCompressorConfig": ("optimiser.transforms.diff_compressor", "DiffCompressorConfig"),
    "DiffCompressionResult": (
        "optimiser.transforms.diff_compressor",
        "DiffCompressionResult",
    ),
    # Code-aware compression (AST-based)
    "CodeAwareCompressor": ("optimiser.transforms.code_compressor", "CodeAwareCompressor"),
    "CodeCompressorConfig": ("optimiser.transforms.code_compressor", "CodeCompressorConfig"),
    "CodeCompressionResult": (
        "optimiser.transforms.code_compressor",
        "CodeCompressionResult",
    ),
    "CodeLanguage": ("optimiser.transforms.code_compressor", "CodeLanguage"),
    "DocstringMode": ("optimiser.transforms.code_compressor", "DocstringMode"),
    "detect_language": ("optimiser.transforms.code_compressor", "detect_language"),
    "is_tree_sitter_available": (
        "optimiser.transforms.code_compressor",
        "is_tree_sitter_available",
    ),
    # Content routing
    "ContentRouter": ("optimiser.transforms.content_router", "ContentRouter"),
    "ContentRouterConfig": ("optimiser.transforms.content_router", "ContentRouterConfig"),
    "RouterCompressionResult": (
        "optimiser.transforms.content_router",
        "RouterCompressionResult",
    ),
    "CompressionStrategy": ("optimiser.transforms.content_router", "CompressionStrategy"),
    # Other transforms
    "CacheAligner": ("optimiser.transforms.cache_aligner", "CacheAligner"),
    # HTML extraction (optional dependency - requires trafilatura)
    "HTMLExtractor": ("optimiser.transforms.html_extractor", "HTMLExtractor"),
    "HTMLExtractorConfig": ("optimiser.transforms.html_extractor", "HTMLExtractorConfig"),
    "HTMLExtractionResult": ("optimiser.transforms.html_extractor", "HTMLExtractionResult"),
    "is_html_content": ("optimiser.transforms.html_extractor", "is_html_content"),
}


def __getattr__(name: str) -> object:
    if name == "__path__":
        raise AttributeError(name)
    if name == "_HTML_EXTRACTOR_AVAILABLE":
        return _HTML_EXTRACTOR_AVAILABLE

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
