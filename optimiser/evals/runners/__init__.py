"""Evaluation runners for different scenarios."""

from optimiser.evals.runners.before_after import BeforeAfterRunner
from optimiser.evals.runners.compression_only import CompressionOnlyRunner

__all__ = ["BeforeAfterRunner", "CompressionOnlyRunner"]
