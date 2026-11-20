"""Native Lodestar-Z SSZ bindings for Electra, Fulu, and Gloas."""

from importlib.metadata import version

from ._metadata import FORKS, PRESETS, SPEC_VERSION, UPSTREAM_COMMIT
from ._native import SSZError
from ._schema import Schema
from .types import SSZType, get_type, list_types
from .value import NativeValue

__all__ = [
    "FORKS",
    "PRESETS",
    "SPEC_VERSION",
    "UPSTREAM_COMMIT",
    "NativeValue",
    "SSZError",
    "SSZType",
    "Schema",
    "get_type",
    "list_types",
]
__version__ = version("ssz-z-python")
