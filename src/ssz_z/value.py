"""Immutable SSZ-backed values with Python-managed lifetimes."""

import hashlib
import json
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._native import MAX_INPUT_SIZE, Operation, SSZError

if TYPE_CHECKING:
    from .types import SSZType


def input_bytes(data: bytes | bytearray | memoryview) -> bytes:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("SSZ data must be bytes-like")
    size = data.nbytes if isinstance(data, memoryview) else len(data)
    if size > MAX_INPUT_SIZE:
        raise SSZError(f"Input exceeds {MAX_INPUT_SIZE} bytes")
    return bytes(data)


class _Layout:
    """Precompute field positions once, rather than traverse values for projections."""

    def __init__(self, schema):
        self.kind = schema["kind"]
        self.fields = {}
        if self.kind == "uint":
            self.size = schema["bits"] // 8
        elif self.kind == "bool":
            self.size = 1
        elif self.kind == "bytevector":
            self.size = schema["length"]
        elif self.kind == "bitvector":
            self.size = (schema["length"] + 7) // 8
        elif self.kind == "vector":
            element = _Layout(schema["element"])
            self.size = None if element.size is None else element.size * schema["length"]
        elif self.kind == "container":
            offset = 0
            variable = []
            for name, child_schema in schema["fields"].items():
                child = _Layout(child_schema)
                self.fields[name] = (child, offset, None)
                if child.size is None:
                    variable.append(name)
                offset += 4 if child.size is None else child.size
            for name, following in zip(variable, variable[1:], strict=False):
                child, start, _ = self.fields[name]
                self.fields[name] = (child, start, self.fields[following][1])
            self.size = None if variable else offset
        else:
            self.size = None

    def field(self, data, name):
        try:
            child, offset, next_offset = self.fields[name]
        except KeyError as error:
            raise ValueError(f"Unknown container field {name!r}") from error
        if child.size is None:
            start = struct.unpack_from("<I", data, offset)[0]
            end = (
                len(data) if next_offset is None else struct.unpack_from("<I", data, next_offset)[0]
            )
        else:
            start, end = offset, offset + child.size
        return child, data[start:end]

    def scalar(self, data):
        if self.kind == "uint":
            return int.from_bytes(data, "little")
        if self.kind == "bool":
            return bool(data[0])
        if self.kind in {"bytevector", "bytelist", "bitvector", "bitlist"}:
            return bytes(data)
        raise TypeError(
            "field() projects scalars/byte fields; use to_obj() for a full Python value"
        )


@dataclass(frozen=True, slots=True, init=False)
class NativeValue:
    """Immutable, validated SSZ bytes with cached roots and block projections.

    Obtain a value with SSZType.load_ssz/load_json/load_obj. Python manages its
    lifetime; returned bytes and derived values are independent of the source.
    """

    codec: "SSZType"
    _ssz: bytes = field(repr=False)
    _root: bytes | None = field(repr=False, compare=False)

    def __init__(self, codec: "SSZType", data: bytes | bytearray | memoryview):
        data = input_bytes(data)
        codec._call(Operation.VALIDATE_SSZ, data)
        self._initialize(codec, data)

    def _initialize(self, codec, data):
        object.__setattr__(self, "codec", codec)
        object.__setattr__(self, "_ssz", data)
        object.__setattr__(self, "_root", None)

    @classmethod
    def _from_validated(cls, codec, data):
        value = cls.__new__(cls)
        value._initialize(codec, data)
        return value

    def to_ssz(self) -> bytes:
        return self._ssz

    def to_json(self) -> bytes:
        """Encode consensus JSON directly in Zig, without Python materialization."""
        return self.codec._call(Operation.SSZ_TO_JSON, self._ssz)

    def to_obj(self) -> Any:
        """Materialize an independent Python dict/list/int/bytes value for editing."""
        return self.codec.deserialize(self._ssz)

    def to_json_value(self) -> Any:
        """Materialize a JSON-compatible value; to_json() is the wire fast path."""
        return json.loads(self.to_json())

    def hash_tree_root(self) -> bytes:
        root = self._root
        if root is None:
            root = self.codec._call(Operation.HASH_TREE_ROOT, self._ssz)
            object.__setattr__(self, "_root", root)
        return root

    def field(self, path: str | tuple[str, ...]) -> Any:
        """Project a scalar/byte field from nested containers without a native call."""
        if isinstance(path, str):
            path = tuple(path.split("."))
        if not isinstance(path, tuple) or not path or not all(isinstance(p, str) for p in path):
            raise TypeError("field path must be a dot-separated string or tuple of field names")
        data = memoryview(self._ssz)
        layout = self.codec._layout
        for part in path:
            layout, data = layout.field(data, part)
        return layout.scalar(data)

    def sign(self, signature: str | bytes | bytearray | memoryview) -> "NativeValue":
        """Attach an existing BLS signature with one buffer allocation and no FFI calls.

        This wraps a signature; it does not perform BLS signing or verification.
        The returned value owns its bytes independently of this value's lifetime.
        """
        if isinstance(signature, str):
            if not signature.startswith("0x") or len(signature) != 194:
                raise SSZError("Signature must contain exactly 96 bytes")
            try:
                signature = bytes.fromhex(signature[2:])
            except ValueError as error:
                raise SSZError("Invalid signature hex") from error
        else:
            signature = input_bytes(signature)
        if len(signature) != 96:
            raise SSZError("Signature must contain exactly 96 bytes")
        data = self._ssz
        target = self.codec._signed_codec
        parts = (
            (struct.pack("<I", 100), signature, data)
            if self.codec._layout.size is None
            else (data, signature)
        )
        size = sum(len(part) for part in parts)
        if size > MAX_INPUT_SIZE:
            raise SSZError(f"Signed output exceeds {MAX_INPUT_SIZE} bytes")
        signed = NativeValue._from_validated(target, b"".join(parts))
        if self._root is not None:
            sig_root = hashlib.sha256(
                hashlib.sha256(signature[:64]).digest()
                + hashlib.sha256(signature[64:] + bytes(32)).digest()
            ).digest()
            object.__setattr__(signed, "_root", hashlib.sha256(self._root + sig_root).digest())
        return signed

    def __repr__(self) -> str:
        return (
            f"NativeValue({self.codec.name}, {self.codec.fork}/{self.codec.preset}, "
            f"{len(self._ssz)} bytes)"
        )
