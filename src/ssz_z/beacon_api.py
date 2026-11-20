"""Beacon API block operations, separate from generic SSZ values."""

import struct
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import Any, cast

from ._json import JSONValue, decode_metadata
from ._native import MAX_INPUT_SIZE, Operation, SSZError, call
from .types import SSZType, get_type
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

    def __post_init__(self) -> None:
        if not isinstance(self.value, NativeValue):
            raise TypeError("BlockValue requires a NativeValue")
        if self.value.codec.fork == "gloas" and self.value.codec.name == "BeaconBlockContents":
            raise ValueError("Use GloasProposal for Gloas block contents")
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

    def _block_path(self) -> tuple[str, ...]:
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
        return cast(int, self.value.field((*self._block_path(), "slot")))

    @property
    def builder_index(self) -> int:
        return cast(
            int,
            self.value.field(
                (
                    *self._block_path(),
                    "body",
                    "signed_execution_payload_bid",
                    "message",
                    "builder_index",
                )
            ),
        )

    def sign(self, signature: str | bytes | bytearray | memoryview) -> "BlockValue":
        if self.value.codec.name != "BeaconBlockContents":
            signed = self.value.sign(signature)
        else:
            signed = _signed_contents(
                self.value, "block", "SignedBeaconBlockContents", "signed_block", signature
            )
        result = BlockValue(signed)
        object.__setattr__(result, "_projection", self._projection)
        return result


def _signed_contents(
    value: NativeValue,
    message_field: str,
    target_name: str,
    signed_field: str,
    signature: str | bytes | bytearray | memoryview,
) -> NativeValue:
    signature = _signature_bytes(signature)
    target = get_type(target_name, fork=value.codec.fork, preset=value.codec.preset)
    message_schema = target._schema["fields"][signed_field]["fields"]["message"]
    if message_schema != value.codec._schema["fields"][message_field]:
        raise ValueError("Incompatible signed contents schema")
    data = memoryview(value.to_ssz())
    source = value.codec._layout
    message = (source.field(data, message_field)[1],)
    signed = target._layout.fields[signed_field][0].container_parts(
        {"message": message, "signature": (signature,)}
    )
    fields = {
        name: (source.field(data, name)[1],)
        for name in target._layout.fields
        if name != signed_field
    }
    parts = target._layout.container_parts({signed_field: signed, **fields})
    return NativeValue._from_validated(target, b"".join(parts))


@dataclass(frozen=True)
class GloasProposal:
    """Separate Gloas beacon-block publication from execution-payload revelation."""

    value: NativeValue

    def __post_init__(self) -> None:
        if not isinstance(self.value, NativeValue):
            raise TypeError("GloasProposal requires a NativeValue")
        if self.value.codec.fork != "gloas" or self.value.codec.name not in {
            "BeaconBlock",
            "BeaconBlockContents",
        }:
            raise ValueError("Expected a Gloas block or block contents")

    @property
    def payload_included(self) -> bool:
        return self.value.codec.name == "BeaconBlockContents"

    @cached_property
    def block(self) -> BlockValue:
        if not self.payload_included:
            return BlockValue(self.value)
        codec = get_type("BeaconBlock", fork="gloas", preset=self.value.codec.preset)
        if self.value.codec._schema["fields"]["block"] != codec._schema:
            raise ValueError("Incompatible Gloas block schema")
        _, data = self.value.codec._layout.field(memoryview(self.value.to_ssz()), "block")
        return BlockValue(NativeValue._from_validated(codec, bytes(data)))

    @property
    def is_self_build(self) -> bool:
        return self.block.builder_index == (1 << 64) - 1

    def sign_block(self, signature: str | bytes | bytearray | memoryview) -> NativeValue:
        """Attach a block signature; the publication contains only the signed block."""
        return self.block.sign(signature).value

    def sign_payload(
        self,
        signature: str | bytes | bytearray | memoryview,
        *,
        envelope: NativeValue | None = None,
    ) -> NativeValue:
        """Attach a payload signature, retaining proof/blob data for stateless publication.

        A stateful proposal requires the caller to fetch its envelope from the
        producing beacon node and pass it explicitly. Builder bids are revealed
        by the builder and cannot use this method.
        """
        if not self.is_self_build:
            raise ValueError("The builder must reveal the execution payload for a builder bid")
        prefix: tuple[str, ...]
        if self.payload_included:
            if envelope is not None:
                raise ValueError("The proposal already includes its execution payload envelope")
            source, prefix = self.value, ("execution_payload_envelope",)
        else:
            if envelope is None:
                raise ValueError(
                    "Fetch the execution payload envelope from the producing beacon node"
                )
            codec = get_type(
                "ExecutionPayloadEnvelope", fork="gloas", preset=self.value.codec.preset
            )
            if not isinstance(envelope, NativeValue):
                raise TypeError("envelope must be a NativeValue")
            codec._check_value(envelope)
            source, prefix = envelope, ()
        expected = {
            ("beacon_block_root",): self.block.block_hash_tree_root(),
            ("parent_beacon_block_root",): self.block.value.field("parent_root"),
            ("builder_index",): self.block.builder_index,
            ("payload", "slot_number"): self.block.slot,
        }
        for path, value in expected.items():
            if source.field((*prefix, *path)) != value:
                raise SSZError(
                    f"Execution payload envelope does not match proposal: {'.'.join(path)}"
                )
        if self.payload_included:
            return _signed_contents(
                self.value,
                "execution_payload_envelope",
                "SignedExecutionPayloadEnvelopeContents",
                "signed_execution_payload_envelope",
                signature,
            )
        return source.sign(signature)


_HEADER_FIELDS = {
    "eth-consensus-version": "version",
    "eth-execution-payload-blinded": "execution_payload_blinded",
    "eth-execution-payload-value": "execution_payload_value",
    "eth-consensus-block-value": "consensus_block_value",
    "eth-execution-payload-source": "execution_payload_source",
    "eth-execution-payload-included": "execution_payload_included",
    "eth-builder-url": "builder_url",
}


type MetadataValue = (
    None | bool | int | float | str | tuple[MetadataValue, ...] | Mapping[str, MetadataValue]
)


def _freeze(value: JSONValue | MetadataValue) -> MetadataValue:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(map(_freeze, value))
    return value


@dataclass(frozen=True)
class BlockResponse:
    """A decoded Beacon API payload and its immutable response metadata."""

    value: NativeValue
    metadata: Mapping[str, MetadataValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze(dict(self.metadata)))

    @cached_property
    def proposal(self) -> "BlockValue | GloasProposal":
        return (
            GloasProposal(self.value)
            if self.value.codec.fork == "gloas"
            else BlockValue(self.value)
        )


def _metadata_value(key: str, value: JSONValue | MetadataValue) -> JSONValue | MetadataValue:
    if key in {"execution_payload_blinded", "execution_payload_included"}:
        if type(value) is not bool:
            raise SSZError(f"Invalid {key} metadata: expected a JSON boolean")
    if key in {"execution_payload_value", "consensus_block_value"}:
        if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 78:
            value = int(value)
        if type(value) is not int or not 0 <= value < 1 << 256:
            raise SSZError(f"Invalid {key} metadata")
    return value


def _header_metadata(headers: Mapping[str, str] | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    value: Any
    for header, raw_value in (headers or {}).items():
        value = raw_value
        key = _HEADER_FIELDS.get(header.lower())
        if key is None:
            continue
        if key in {"execution_payload_blinded", "execution_payload_included"}:
            if value not in {"true", "false"}:
                raise SSZError(f"Invalid {header} header")
            value = value == "true"
        value = _metadata_value(key, value)
        if key in metadata and metadata[key] != value:
            raise SSZError(f"Conflicting response metadata for {key}")
        metadata[key] = value
    fork = metadata.get("version")
    if not isinstance(fork, str) or fork not in {"electra", "fulu", "gloas"}:
        raise SSZError("Expected Electra, Fulu, or Gloas response version")
    flag = "execution_payload_included" if fork == "gloas" else "execution_payload_blinded"
    if type(metadata.get(flag)) is not bool:
        raise SSZError(f"Missing or invalid {flag} metadata")
    if fork == "gloas" and "execution_payload_blinded" in metadata:
        if metadata["execution_payload_blinded"] is not False:
            raise SSZError("Gloas proposals cannot use blinded block metadata")
    return metadata


def _proposal_codec(metadata: Mapping[str, Any], preset: str) -> SSZType:
    if metadata["version"] == "gloas":
        name = "BeaconBlockContents" if metadata["execution_payload_included"] else "BeaconBlock"
    else:
        name = (
            "BlindedBeaconBlock" if metadata["execution_payload_blinded"] else "BeaconBlockContents"
        )
    return get_type(name, fork=metadata["version"], preset=preset)


def load_proposal_json(
    text: str | bytes | bytearray | memoryview, *, preset: str, headers: Mapping[str, str] | None
) -> BlockResponse:
    """Select a proposal codec from required headers, checking JSON metadata against them."""
    metadata = _header_metadata(headers)
    if isinstance(text, str):
        if len(text) > MAX_INPUT_SIZE:
            raise SSZError("JSON input too large")
        text = text.encode("utf-8")
    text = input_bytes(text)
    envelope = decode_metadata(call(preset, "primitive", "Uint64", Operation.REST_METADATA, text))
    for key, raw_value in envelope["metadata"].items():
        value = _metadata_value(key, raw_value)
        if key in _HEADER_FIELDS.values():
            if key not in metadata:
                raise SSZError(f"Missing response header for {key}")
            if metadata[key] != value:
                raise SSZError(f"Conflicting response metadata for {key}")
        else:
            metadata[key] = value
    codec = _proposal_codec(metadata, preset)
    proposal = codec.load_json(text[envelope["data_start"] : envelope["data_end"]])
    return BlockResponse(proposal, metadata)


def load_proposal_ssz(
    data: bytes | bytearray | memoryview, *, headers: Mapping[str, str] | None, preset: str
) -> BlockResponse:
    """Select the SSZ proposal codec using Beacon API HTTP response headers."""
    metadata = _header_metadata(headers)
    return BlockResponse(_proposal_codec(metadata, preset).load_ssz(data), metadata)
