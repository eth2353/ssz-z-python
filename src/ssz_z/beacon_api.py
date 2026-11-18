"""Beacon API block operations, separate from generic SSZ values."""

import struct
from dataclasses import dataclass, field

from ._native import Operation
from .types import get_type
from .value import NativeValue, _signature_bytes


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
