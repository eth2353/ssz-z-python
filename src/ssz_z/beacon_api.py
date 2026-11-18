"""Beacon API block operations, separate from generic SSZ values."""

import struct
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import Any

from ._native import MAX_INPUT_SIZE, Operation, SSZError, call
from .types import _parse_json, get_type
from .value import NativeValue, _signature_bytes, input_bytes


@dataclass(frozen=True)
class BlockValue:
    """A block or block-contents value with Beacon API projections and signing.

    ``value`` owns the immutable wire value. Signing attaches an existing BLS
    signature; it performs no cryptography.
    """

    value: NativeValue
    _projection: tuple[bytes, bytes] | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self):
        if not isinstance(self.value, NativeValue):
            raise TypeError("BlockValue requires a NativeValue")
        self._block_path()

    def _project_block(self) -> tuple[bytes, bytes]:
        projection = self._projection
        if projection is None:
            data = self.value.codec._call(Operation.BLOCK_PROJECTION, self.value.to_ssz())
            if len(data) != 144:
                raise RuntimeError("Invalid block projection from native library")
            projection = (data[:112], data[112:])
            object.__setattr__(self, "_projection", projection)
            if self.value.codec.name in {"BeaconBlock", "BlindedBeaconBlock"}:
                object.__setattr__(self.value, "_root", projection[1])
        return projection

    def header_dict(self) -> dict[str, str]:
        """Return a BeaconBlockHeader in consensus JSON form, using one body hash."""
        data = self._project_block()[0]
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
        return self._project_block()[1]

    def _block_path(self):
        name = self.value.codec.name
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
        return self.value.field((*self._block_path(), "slot"))

    @property
    def builder_index(self) -> int:
        return self.value.field(
            (
                *self._block_path(),
                "body",
                "signed_execution_payload_bid",
                "message",
                "builder_index",
            )
        )

    def sign(self, signature: str | bytes | bytearray | memoryview) -> "BlockValue":
        if self.value.codec.name != "BeaconBlockContents":
            signed = self.value.sign(signature)
        else:
            signature = _signature_bytes(signature)
            target = get_type(
                "SignedBeaconBlockContents",
                fork=self.value.codec.fork,
                preset=self.value.codec.preset,
            )
            data = memoryview(self.value.to_ssz())
            fields = {
                name: (self.value.codec._layout.field(data, name)[1],)
                for name in self.value.codec._layout.fields
            }
            signed_block = target._layout.fields["signed_block"][0].container_parts(
                {"message": fields.pop("block"), "signature": (signature,)}
            )
            parts = target._layout.container_parts({"signed_block": signed_block, **fields})
            signed = NativeValue._from_validated(target, b"".join(parts))
        result = BlockValue(signed)
        object.__setattr__(result, "_projection", self._projection)
        return result


_HEADER_FIELDS = {
    "eth-consensus-version": "version",
    "eth-execution-payload-blinded": "execution_payload_blinded",
    "eth-execution-payload-value": "execution_payload_value",
    "eth-consensus-block-value": "consensus_block_value",
    "eth-execution-payload-source": "execution_payload_source",
}


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(map(_freeze, value))
    return value


@dataclass(frozen=True)
class BlockResponse:
    """A decoded Beacon API payload and its immutable response metadata."""

    value: NativeValue
    metadata: Mapping[str, Any]

    def __post_init__(self):
        object.__setattr__(self, "metadata", _freeze(dict(self.metadata)))

    @cached_property
    def proposal(self) -> BlockValue:
        return BlockValue(self.value)


def _metadata_value(key, value):
    if key in {"execution_payload_value", "consensus_block_value"}:
        if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 78:
            value = int(value)
        if type(value) is not int or not 0 <= value < 1 << 256:
            raise SSZError(f"Invalid {key} metadata")
    return value


def _response_metadata(metadata, headers):
    metadata = {key: _metadata_value(key, value) for key, value in metadata.items()}
    for header, value in (headers or {}).items():
        key = _HEADER_FIELDS.get(header.lower())
        if key is None:
            continue
        if key == "execution_payload_blinded":
            if value not in {"true", "false"}:
                raise SSZError(f"Invalid {header} header")
            value = value == "true"
        value = _metadata_value(key, value)
        if key in metadata and metadata[key] != value:
            raise SSZError(f"Conflicting response metadata for {key}")
        metadata[key] = value
    if metadata.get("version") not in {"electra", "fulu"}:
        raise SSZError("Expected Electra or Fulu response version")
    if type(metadata.get("execution_payload_blinded")) is not bool:
        raise SSZError("Missing or invalid execution_payload_blinded metadata")
    return metadata


def _proposal_codec(metadata, preset):
    return get_type(
        "BlindedBeaconBlock" if metadata["execution_payload_blinded"] else "BeaconBlockContents",
        fork=metadata["version"],
        preset=preset,
    )


def load_proposal_json(text, *, preset="mainnet", headers=None) -> BlockResponse:
    """Select a proposal codec from JSON metadata without decoding its data in Python."""
    if isinstance(text, str):
        if len(text) > MAX_INPUT_SIZE:
            raise SSZError("JSON input too large")
        text = text.encode("utf-8")
    text = input_bytes(text)
    envelope = _parse_json(call(preset, "primitive", "Uint64", Operation.REST_METADATA, text))
    metadata = _response_metadata(envelope["metadata"], headers)
    codec = _proposal_codec(metadata, preset)
    value = codec.load_json(text[envelope["data_start"] : envelope["data_end"]])
    return BlockResponse(value, metadata)


def load_proposal_ssz(data, *, headers, preset="mainnet") -> BlockResponse:
    """Select the SSZ proposal codec using Beacon API HTTP response headers."""
    metadata = _response_metadata({}, headers)
    return BlockResponse(_proposal_codec(metadata, preset).load_ssz(data), metadata)
