"""Consensus codecs loading wire documents into immutable SSZ-backed values."""

import copy
import json
from dataclasses import dataclass, field
from functools import cached_property, lru_cache

from ._native import FORKS, MAX_INPUT_SIZE, PRESETS, Operation, SSZError, call
from ._schema import Schema
from .value import NativeValue, _Layout, input_bytes


@dataclass(frozen=True)
class SSZType:
    """A fork- and preset-specific Lodestar-Z codec. Obtain with :func:`get_type`."""

    name: str
    fork: str
    preset: str
    _schema: Schema = field(repr=False, compare=False, hash=False)

    @property
    def schema(self) -> Schema:
        """Return a copy of the schema reflected from the upstream Zig type."""
        return copy.deepcopy(self._schema)

    def _call(self, operation: Operation, data: bytes = b"") -> bytes:
        return call(self.preset, self.fork, self.name, operation, data)

    def default(self) -> NativeValue:
        """Return the canonical default value as immutable SSZ bytes."""
        return NativeValue._from_validated(self, self._call(Operation.DEFAULT_SSZ))

    @cached_property
    def _layout(self) -> _Layout:
        return _Layout(self._schema)

    @cached_property
    def _signed_codec(self) -> "SSZType":
        target = get_type("Signed" + self.name, fork=self.fork, preset=self.preset)
        fields = target._schema.get("fields", {})
        if (
            tuple(fields) != ("message", "signature")
            or fields["message"] != self._schema
            or fields["signature"] != {"kind": "bytevector", "length": 96}
        ):
            raise ValueError("No compatible signed wrapper for this value")
        return target

    def _check_value(self, value: NativeValue) -> None:
        if value.codec != self:
            raise ValueError("SSZ value belongs to a different type, fork, or preset")

    def load_ssz(self, data: bytes | bytearray | memoryview) -> NativeValue:
        """Validate SSZ in one native call and retain immutable bytes without decoding."""
        return NativeValue(self, data)

    def load_json(
        self, text: str | bytes | bytearray | memoryview, *, wrapped: bool = False
    ) -> NativeValue:
        """Load a complete JSON document; wrapped=True selects a REST data field.

        Accepts UTF-8 bytes or text, never decoded Python objects. Scalars must
        also be complete JSON documents (for example, a quoted hex string).
        """
        if isinstance(text, str):
            if len(text) > MAX_INPUT_SIZE:
                raise SSZError("JSON input too large")
            text = text.encode("utf-8")
        else:
            text = input_bytes(text)
        data = self._call(Operation.REST_JSON_TO_SSZ if wrapped else Operation.JSON_TO_SSZ, text)
        return NativeValue._from_validated(self, data)

    def hash_tree_root_from_ssz(self, data: bytes | bytearray | memoryview) -> bytes:
        """Validate and hash serialized SSZ directly without materializing its value."""
        return self._call(Operation.HASH_TREE_ROOT, input_bytes(data))


def _check(fork: str, preset: str) -> None:
    if fork not in (*FORKS, "primitive"):
        raise ValueError(f"Unknown fork {fork!r}; choose from {FORKS} or 'primitive'")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}; choose from {PRESETS}")


@lru_cache(maxsize=12)
def list_types(*, fork: str, preset: str) -> tuple[str, ...]:
    """List canonical SSZ type names for an explicitly selected fork."""
    _check(fork, preset)
    return tuple(json.loads(call(preset, fork, "", Operation.LIST_TYPES)))


@lru_cache(maxsize=4096)
def get_type(name: str, *, fork: str, preset: str) -> SSZType:
    """Select a type with an explicit fork; use fork="primitive" for primitives."""
    _check(fork, preset)
    namespace = fork
    if name not in list_types(fork=fork, preset=preset):
        if name in list_types(fork="primitive", preset=preset):
            namespace = "primitive"
        else:
            raise ValueError(f"Unknown SSZ type {name!r} for {fork}/{preset}")
    schema = json.loads(call(preset, namespace, name, Operation.TYPE_SCHEMA))
    return SSZType(name, namespace, preset, schema)
