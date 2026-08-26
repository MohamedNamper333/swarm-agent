"""
Placeholder Package - SmartPlaceholder for offline/test model responses.

Restructured (2026-08-25): an empty package directory shadowed placeholder.py,
breaking imports across tests and fallback_chain. Re-exports the real module.
"""
from swarm.enterprise.core.placeholder.core import (
    ModelType,
    PlaceholderResponse,
    SmartPlaceholder,
    classify_model,
    get_default_placeholder,
    smart_placeholder_call,
)

__all__ = [
    "ModelType",
    "PlaceholderResponse",
    "SmartPlaceholder",
    "classify_model",
    "get_default_placeholder",
    "smart_placeholder_call",
]
