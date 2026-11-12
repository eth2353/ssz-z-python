"""Immutable, validated SSZ-backed values with explicit, Python-owned lifetimes."""

import hashlib
import json
import struct
from threading import RLock
from typing import TYPE_CHECKING, Any

from ._native import MAX_INPUT_SIZE, Operation, SSZError, call

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


class NativeValue:
    """A validated immutable SSZ buffer; no foreign pointer survives a native call.

    Use SSZType.load_ssz/load_json/load_obj to create one. to_ssz() returns the
    retained bytes without copying; projections and hashing skip Python trees.
    close() is idempotent and waits for operations on this value to finish.
    Bytes already returned to a caller remain valid after close().
    """

    __slots__ = ("_codec", "_ssz", "_root", "_header", "_block_root", "_lock")

    def __init__(self, codec: "SSZType", data: bytes | bytearray | memoryview):
        data = input_bytes(data)
        call(codec.preset, codec.fork, codec.name, Operation.VALIDATE_SSZ, data)
        self._initialize(codec, data)

    def _initialize(self, codec, data):
        self._codec = codec
        self._ssz = data
        self._root = None
        self._header = None
        self._block_root = None
        self._lock = RLock()

    @classmethod
    def _from_validated(cls, codec, data):
        value = cls.__new__(cls)
        value._initialize(codec, data)
        return value

    @property
    def codec(self) -> "SSZType":
        return self._codec

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._ssz is None

    def _data(self):
        if self._ssz is None:
            raise ValueError("SSZ value is closed")
        return self._ssz

    def close(self) -> None:
        with self._lock:
            self._ssz = None
            self._root = self._header = self._block_root = None

    def __enter__(self) -> "NativeValue":
        with self._lock:
            self._data()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def to_ssz(self) -> bytes:
        with self._lock:
            return self._data()

    def to_json(self) -> bytes:
        """Encode consensus JSON directly in Zig, without Python materialization."""
        with self._lock:
            return call(
                self.codec.preset,
                self.codec.fork,
                self.codec.name,
                Operation.SSZ_TO_JSON,
                self._data(),
            )

    def to_obj(self) -> Any:
        """Materialize an independent Python dict/list/int/bytes value for editing."""
        with self._lock:
            return self.codec.deserialize(self._data())

    def to_json_value(self) -> Any:
        """Materialize a JSON-compatible value; to_json() is the wire fast path."""
        return json.loads(self.to_json())

    def hash_tree_root(self) -> bytes:
        with self._lock:
            data = self._data()
            if self._root is None:
                if self.codec.name in {"BeaconBlock", "BlindedBeaconBlock"}:
                    self._project_block()
                    self._root = self._block_root
                else:
                    self._root = call(
                        self.codec.preset,
                        self.codec.fork,
                        self.codec.name,
                        Operation.HASH_TREE_ROOT,
                        data,
                    )
            return self._root

    def _project_block(self):
        data = self._data()
        if self._header is None:
            projection = call(
                self.codec.preset,
                self.codec.fork,
                self.codec.name,
                Operation.BLOCK_PROJECTION,
                data,
            )
            if len(projection) != 144:
                raise RuntimeError("Invalid block projection from native library")
            self._header, self._block_root = projection[:112], projection[112:]
            if self.codec.name in {"BeaconBlock", "BlindedBeaconBlock"}:
                self._root = self._block_root

    def header_dict(self) -> dict[str, str]:
        """Return a BeaconBlockHeader in consensus JSON form, using one body hash."""
        with self._lock:
            self._project_block()
            data = self._header
            slot, proposer = struct.unpack_from("<QQ", data)
            return {
                "slot": str(slot),
                "proposer_index": str(proposer),
                "parent_root": "0x" + data[16:48].hex(),
                "state_root": "0x" + data[48:80].hex(),
                "body_root": "0x" + data[80:112].hex(),
            }

    def block_hash_tree_root(self) -> bytes:
        """Hash the unsigned block, including when this value is a contents envelope."""
        with self._lock:
            self._project_block()
            return self._block_root

    def field(self, path: str | tuple[str, ...]) -> Any:
        """Project a scalar/byte field from nested containers without a native call."""
        if isinstance(path, str):
            path = tuple(path.split("."))
        if not isinstance(path, tuple) or not path or not all(isinstance(p, str) for p in path):
            raise TypeError("field path must be a dot-separated string or tuple of field names")
        with self._lock:
            data = memoryview(self._data())
            layout = self.codec._layout
            for part in path:
                layout, data = layout.field(data, part)
            return layout.scalar(data)

    def _block_path(self):
        name = self.codec.name
        if name == "BeaconBlockContents":
            return ("block",)
        if name == "SignedBeaconBlockContents":
            return ("signed_block", "message")
        if name in {"SignedBeaconBlock", "SignedBlindedBeaconBlock"}:
            return ("message",)
        if name in {"BeaconBlock", "BlindedBeaconBlock"}:
            return ()
        raise ValueError(f"{name} is not a block type")

    @property
    def slot(self) -> int:
        return self.field((*self._block_path(), "slot"))

    @property
    def builder_index(self) -> int:
        if self.codec.name in {"ExecutionPayloadEnvelope", "SignedExecutionPayloadEnvelope"}:
            prefix = ("message",) if self.codec.name.startswith("Signed") else ()
            return self.field((*prefix, "builder_index"))
        return self.field(
            (
                *self._block_path(),
                "body",
                "signed_execution_payload_bid",
                "message",
                "builder_index",
            )
        )

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
        with self._lock:
            data = self._data()
            target = self.codec._signed_codec
            if self.codec.name == "BeaconBlockContents":
                a, b, c = struct.unpack_from("<III", data)
                parts = (
                    struct.pack("<III", a, b + 100, c + 100),
                    struct.pack("<I", 100),
                    signature,
                    memoryview(data)[a:],
                )
            else:
                parts = (
                    (struct.pack("<I", 100), signature, data)
                    if self.codec._layout.size is None
                    else (data, signature)
                )
            size = sum(len(part) for part in parts)
            if size > MAX_INPUT_SIZE:
                raise SSZError(f"Signed output exceeds {MAX_INPUT_SIZE} bytes")
            signed = NativeValue._from_validated(target, b"".join(parts))
            signed._header, signed._block_root = self._header, self._block_root
            if self.codec.name != "BeaconBlockContents" and self._root is not None:
                chunks = [signature[i : i + 32].ljust(32, b"\0") for i in range(0, 96, 32)]
                sig_root = hashlib.sha256(
                    hashlib.sha256(chunks[0] + chunks[1]).digest()
                    + hashlib.sha256(chunks[2] + bytes(32)).digest()
                ).digest()
                signed._root = hashlib.sha256(self._root + sig_root).digest()
            return signed

    def __repr__(self) -> str:
        with self._lock:
            state = "closed" if self._ssz is None else f"{len(self._ssz)} bytes"
            return f"NativeValue({self.codec.name}, {self.codec.fork}/{self.codec.preset}, {state})"
