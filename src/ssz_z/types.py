"""Consensus codecs using Python integers, bytes, dictionaries, and lists."""

import copy
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from typing import Any

from ._native import FORKS, MAX_INPUT_SIZE, PRESETS, Operation, SSZError, call
from .value import NativeValue, _Layout, input_bytes

_DECIMAL = re.compile(r"[0-9]+\Z", re.ASCII)


def _normalize(schema: dict, value: Any, path: str, *, python: bool = False) -> Any:
    kind = schema["kind"]
    if kind == "container":
        if not isinstance(value, Mapping):
            raise SSZError(f"{path}: expected a mapping")
        fields = schema["fields"]
        missing, extra = fields.keys() - value.keys(), value.keys() - fields.keys()
        if missing or extra:
            raise SSZError(
                f"{path}: missing fields {sorted(missing)!r}; "
                f"unknown fields {sorted(extra, key=str)!r}"
            )
        return {
            key: _normalize(child, value[key], f"{path}.{key}", python=python)
            for key, child in fields.items()
        }
    if kind == "uint":
        if isinstance(value, str) and _DECIMAL.fullmatch(value):
            try:
                value = int(value)
            except ValueError as error:
                raise SSZError(f"{path}: invalid decimal integer") from error
        if type(value) is not int or not 0 <= value < 1 << schema["bits"]:
            raise SSZError(f"{path}: expected uint{schema['bits']}")
        return value if python else str(value)
    if kind == "bool":
        if type(value) is not bool:
            raise SSZError(f"{path}: expected bool")
        return value
    if kind in {"vector", "list"}:
        if not isinstance(value, (list, tuple)):
            raise SSZError(f"{path}: expected a list")
        bound = schema.get("length", schema.get("limit", MAX_INPUT_SIZE))
        if (kind == "vector" and len(value) != bound) or len(value) > bound:
            raise SSZError(f"{path}: invalid {kind} length {len(value)} (bound {bound})")
        return [
            _normalize(schema["element"], item, f"{path}[{index}]", python=python)
            for index, item in enumerate(value)
        ]
    if isinstance(value, str) and value.startswith("0x"):
        try:
            raw = bytes.fromhex(value[2:])
        except ValueError as error:
            raise SSZError(f"{path}: invalid hex") from error
        if len(raw) * 2 != len(value) - 2:
            raise SSZError(f"{path}: hex must have even length and no whitespace")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
    else:
        raise SSZError(f"{path}: expected bytes or 0x-prefixed even-length hex")
    bound = schema.get(
        "length", schema.get("limit", MAX_INPUT_SIZE * 8 if kind == "bitlist" else MAX_INPUT_SIZE)
    )
    if kind == "bytevector" and len(raw) != bound:
        raise SSZError(f"{path}: expected {bound} bytes, got {len(raw)}")
    if kind == "bytelist" and len(raw) > bound:
        raise SSZError(f"{path}: exceeds {bound} bytes")
    if kind == "bitvector":
        if len(raw) != (bound + 7) // 8 or (bound % 8 and raw[-1] >> (bound % 8)):
            raise SSZError(f"{path}: invalid bitvector of {bound} bits")
    if kind == "bitlist":
        if not raw or raw[-1] == 0 or (len(raw) - 1) * 8 + raw[-1].bit_length() - 1 > bound:
            raise SSZError(f"{path}: invalid bitlist or exceeds {bound} bits")
    return raw if python else "0x" + raw.hex()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SSZError(f"Duplicate JSON field {key!r}")
        result[key] = value
    return result


def _parse_json(value, *, scalar_strings=True):
    if (
        scalar_strings
        and isinstance(value, str)
        and (value.startswith("0x") or _DECIMAL.fullmatch(value))
    ):
        return value
    if isinstance(value, (str, bytes, bytearray)):
        if len(value) > MAX_INPUT_SIZE:
            raise SSZError("JSON input too large")
        try:
            return json.loads(value, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise SSZError(f"Invalid JSON: {error}") from error
    return value


@dataclass(frozen=True)
class SSZType:
    """A fork- and preset-specific Lodestar-Z codec. Obtain with :func:`get_type`."""

    name: str
    fork: str
    preset: str
    _schema: dict = field(repr=False, compare=False, hash=False)

    @property
    def schema(self) -> dict:
        """Return a copy of the schema reflected from the upstream Zig type."""
        return copy.deepcopy(self._schema)

    def _call(self, operation: Operation, data: bytes = b"") -> bytes:
        return call(self.preset, self.fork, self.name, operation, data)

    def serialize(self, value: Any) -> bytes:
        """Encode a Python value as canonical SSZ bytes."""
        if isinstance(value, NativeValue):
            self._check_value(value)
            return value.to_ssz()
        normalized = _normalize(self._schema, value, self.name)
        encoded = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode()
        return self._call(Operation.JSON_TO_SSZ, encoded)

    def deserialize(self, data: bytes | bytearray | memoryview) -> Any:
        """Validate and decode SSZ into integers, bytes, dicts and lists."""
        encoded = self._call(Operation.SSZ_TO_JSON, input_bytes(data))
        return _normalize(self._schema, json.loads(encoded), self.name, python=True)

    def from_json(self, value: Any) -> Any:
        """Decode a JSON-compatible value or JSON text into a Python value."""
        return _normalize(self._schema, _parse_json(value), self.name, python=True)

    def to_json(self, value: Any) -> Any:
        """Encode as consensus JSON: decimal strings and 0x-prefixed hex."""
        if isinstance(value, NativeValue):
            self._check_value(value)
            return value.to_json_value()
        return _normalize(self._schema, value, self.name)

    def dumps(self, value: Any, **kwargs) -> str:
        """Return consensus JSON text; keyword arguments pass to json.dumps."""
        return json.dumps(self.to_json(value), **kwargs)

    def loads(self, text: str | bytes | bytearray) -> Any:
        """Decode a complete JSON document, rejecting duplicate keys."""
        if not isinstance(text, (str, bytes, bytearray)):
            raise TypeError("JSON text must be str or bytes-like")
        return _normalize(
            self._schema, _parse_json(text, scalar_strings=False), self.name, python=True
        )

    def default(self) -> Any:
        """Return an independent, zero/default Python value."""
        encoded = self._call(Operation.DEFAULT_JSON)
        return _normalize(self._schema, json.loads(encoded), self.name, python=True)

    def hash_tree_root(self, value: Any) -> bytes:
        """Return the 32-byte SSZ root of a Python value."""
        if isinstance(value, NativeValue):
            self._check_value(value)
            return value.hash_tree_root()
        return self.hash_tree_root_from_ssz(self.serialize(value))

    @cached_property
    def _layout(self):
        return _Layout(self._schema)

    @cached_property
    def _signed_codec(self):
        target = get_type("Signed" + self.name, fork=self.fork, preset=self.preset)
        fields = target._schema.get("fields", {})
        if (
            tuple(fields) != ("message", "signature")
            or fields["message"] != self._schema
            or fields["signature"] != {"kind": "bytevector", "length": 96}
        ):
            raise ValueError("No compatible signed wrapper for this value")
        return target

    def _check_value(self, value: NativeValue):
        if value.codec != self:
            raise ValueError("SSZ value belongs to a different type, fork, or preset")

    def load_ssz(self, data: bytes | bytearray | memoryview) -> NativeValue:
        """Validate SSZ in one native call and retain immutable bytes without decoding."""
        return NativeValue(self, data)

    def load_json(
        self, text: str | bytes | bytearray | memoryview, *, wrapped: bool = False
    ) -> NativeValue:
        """Parse JSON directly in Zig; wrapped=True reads a REST response's data field."""
        if isinstance(text, str):
            if len(text) > MAX_INPUT_SIZE:
                raise SSZError("JSON input too large")
            text = text.encode("utf-8")
        else:
            text = input_bytes(text)
        data = self._call(Operation.REST_JSON_TO_SSZ if wrapped else Operation.JSON_TO_SSZ, text)
        return NativeValue._from_validated(self, data)

    def load_obj(self, value: Any) -> NativeValue:
        """Encode a Python value once, retaining its native SSZ fast path."""
        return NativeValue._from_validated(self, self.serialize(value))

    def hash_tree_root_from_ssz(self, data: bytes | bytearray | memoryview) -> bytes:
        """Validate and hash serialized SSZ directly without materializing its value."""
        return self._call(Operation.HASH_TREE_ROOT, input_bytes(data))


def _check(fork: str, preset: str) -> None:
    if fork not in (*FORKS, "primitive"):
        raise ValueError(f"Unknown fork {fork!r}; choose from {FORKS} or 'primitive'")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}; choose from {PRESETS}")


@lru_cache(maxsize=12)
def list_types(*, fork: str = "gloas", preset: str = "mainnet") -> tuple[str, ...]:
    """List the canonical SSZ type names for a fork and preset."""
    _check(fork, preset)
    return tuple(json.loads(call(preset, fork, "", Operation.LIST_TYPES)))


@lru_cache(maxsize=4096)
def get_type(name: str, *, fork: str = "gloas", preset: str = "mainnet") -> SSZType:
    """Select a consensus type; primitive types are also available in every fork."""
    _check(fork, preset)
    namespace = fork
    if name not in list_types(fork=fork, preset=preset):
        if name in list_types(fork="primitive", preset=preset):
            namespace = "primitive"
        else:
            raise ValueError(f"Unknown SSZ type {name!r} for {fork}/{preset}")
    schema = json.loads(call(preset, namespace, name, Operation.TYPE_SCHEMA))
    return SSZType(name, namespace, preset, schema)
