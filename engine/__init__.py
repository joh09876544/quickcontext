"""
Lightweight package initializer for engine.

Avoid importing the full QuickContext SDK on parser-only and CLI startup paths
unless the SDK is actually requested.
"""

from importlib import import_module
from typing import Any


__all__ = ["QuickContext"]


def __getattr__(name: str) -> Any:
    if name == "QuickContext":
        return import_module("engine.sdk").QuickContext
    raise AttributeError(f"module 'engine' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
