"""Static consumer checks; checked by mypy, not executed by pytest."""

from typing import assert_type

from ssz_z import NativeValue, Schema, SSZType, get_type, list_types
from ssz_z.beacon_api import (
    BlockResponse,
    BlockValue,
    GloasProposal,
    load_proposal_json,
    load_proposal_ssz,
)

codec = get_type("BeaconBlock", fork="gloas", preset="minimal")
assert_type(codec, SSZType)
assert_type(codec.schema, Schema)
assert_type(list_types(fork="gloas", preset="minimal"), tuple[str, ...])
value = codec.default()
assert_type(value, NativeValue)
assert_type(codec.load_ssz(memoryview(b"")), NativeValue)
assert_type(codec.load_json(bytearray(b"{}")), NativeValue)
assert_type(value.to_ssz(), bytes)
assert_type(value.to_json(), bytes)
assert_type(value.field("slot"), int | bool | bytes)
assert_type(value.sign(bytes(96)), NativeValue)
block = BlockValue(value)
assert_type(block.slot, int)
assert_type(block.header_dict(), dict[str, str])
assert_type(block.sign(bytes(96)), BlockValue)
proposal = GloasProposal(value)
assert_type(proposal.sign_block(bytes(96)), NativeValue)
assert_type(proposal.sign_payload(bytes(96), envelope=value), NativeValue)
assert_type(load_proposal_json(b"{}", preset="minimal", headers={}), BlockResponse)
assert_type(load_proposal_ssz(b"", preset="minimal", headers={}), BlockResponse)
