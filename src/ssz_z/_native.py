"""Small, ownership-safe ctypes boundary. Importing this module does not load a library."""

import ctypes
import sys
from enum import IntEnum
from functools import lru_cache
from pathlib import Path

PRESETS = ("mainnet", "minimal", "gnosis")
FORKS = ("electra", "fulu", "gloas")
MAX_INPUT_SIZE = 512 * 1024 * 1024
UPSTREAM_COMMIT = "0ac7778d7034693a0818296dbe717f2999576ab1"
SPEC_VERSION = "v1.7.0-beta.4"


class Operation(IntEnum):
    """ABI values mirrored by native/bindings.zig and native/bindings.h."""

    JSON_TO_SSZ = 0
    SSZ_TO_JSON = 1
    HASH_TREE_ROOT = 2
    DEFAULT_SSZ = 3
    TYPE_SCHEMA = 4
    LIST_TYPES = 5
    VALIDATE_SSZ = 6
    REST_JSON_TO_SSZ = 7
    BLOCK_PROJECTION = 8
    REST_METADATA = 9


class SSZError(ValueError):
    """Invalid SSZ, JSON, or a value outside its consensus type's bounds."""


@lru_cache(maxsize=3)
def _library(preset: str):
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}; choose from {PRESETS}")
    filename = (
        f"ssz_z_{preset}.dll"
        if sys.platform == "win32"
        else f"libssz_z_{preset}.{'dylib' if sys.platform == 'darwin' else 'so'}"
    )
    path = Path(__file__).parent / "_native" / filename
    if not path.is_file():
        raise ImportError(
            "Native SSZ libraries are missing. Install with `pip install .` "
            "or build an editable install with `pip install -e .`."
        )
    library = ctypes.CDLL(str(path))
    library.ssz_z_abi_version.restype = ctypes.c_uint32
    if library.ssz_z_abi_version() != 2:
        raise ImportError("Incompatible ssz-z native ABI")
    library.ssz_z_call.argtypes = [
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_uint8,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    library.ssz_z_call.restype = ctypes.c_uint8
    library.ssz_z_free.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    library.ssz_z_free.restype = None
    return library


def call(preset: str, fork: str, name: str, operation: Operation, data: bytes = b"") -> bytes:
    if len(data) > MAX_INPUT_SIZE:
        raise SSZError(f"Input exceeds {MAX_INPUT_SIZE} bytes")
    library = _library(preset)
    output = ctypes.c_void_p()
    size = ctypes.c_size_t()
    fork_bytes, name_bytes = fork.encode("ascii"), name.encode("ascii")
    status = library.ssz_z_call(
        fork_bytes,
        len(fork_bytes),
        name_bytes,
        len(name_bytes),
        operation,
        data,
        len(data),
        ctypes.byref(output),
        ctypes.byref(size),
    )
    try:
        if status == 2:
            raise MemoryError("Native SSZ allocation failed")
        result = ctypes.string_at(output, size.value)
        if status:
            message = result.decode("utf-8")
            if message == "OutOfMemory":
                raise MemoryError("Native SSZ allocation failed")
            raise SSZError(f"{fork}.{name} ({preset}): {message}")
        return result
    finally:
        if output.value:
            library.ssz_z_free(output, size.value)
