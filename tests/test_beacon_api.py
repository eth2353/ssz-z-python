"""Beacon API envelopes, including Fulu's cell-proof list bound."""

import copy
import hashlib
import struct

import pytest

from ssz_z import PRESETS, SSZError, get_type, list_types

FORKS = ("electra", "fulu")
NAMES = (
    "BeaconBlockContents",
    "SignedBeaconBlockContents",
    "BlindedBeaconBlockBody",
    "BlindedBeaconBlock",
    "SignedBlindedBeaconBlock",
)


def merkleize(chunks, limit):
    """Independent sparse Merkle tree for the envelope's proof/blob lists."""
    depth = (limit - 1).bit_length()
    zero = bytes(32)
    nodes = list(chunks)
    assert len(nodes) <= limit
    for _ in range(depth):
        if len(nodes) % 2:
            nodes.append(zero)
        nodes = [hashlib.sha256(nodes[i] + nodes[i + 1]).digest() for i in range(0, len(nodes), 2)]
        zero = hashlib.sha256(zero + zero).digest()
    return nodes[0] if nodes else zero


def byte_vector_root(value):
    chunks = [value[i : i + 32].ljust(32, b"\0") for i in range(0, len(value), 32)]
    return merkleize(chunks, len(chunks))


def composite_list_root(values, limit):
    root = merkleize([byte_vector_root(value) for value in values], limit)
    return hashlib.sha256(root + len(values).to_bytes(32, "little")).digest()


def populated_block(fork, preset):
    codec = get_type("BeaconBlock", fork=fork, preset=preset)
    value = codec.default()
    value.update(slot=123, proposer_index=42, parent_root=b"\x11" * 32, state_root=b"\x22" * 32)
    body = value["body"]
    body["graffiti"] = b"\x33" * 32
    payload = body["execution_payload"]
    payload.update(block_number=17, extra_data=b"hello", transactions=[b"\x01\x02", b"\x03"])
    payload["withdrawals"] = [
        {"index": 1, "validator_index": 2, "address": b"\x44" * 20, "amount": 3},
    ]
    body["blob_kzg_commitments"] = [b"\x55" * 48]
    body["execution_requests"]["withdrawals"] = [
        {"source_address": b"\x66" * 20, "validator_pubkey": b"\x77" * 48, "amount": 8},
    ]
    return value


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", FORKS)
def test_beacon_api_types_and_blinded_roots(fork, preset):
    def codec(name):
        return get_type(name, fork=fork, preset=preset)

    assert set(NAMES) <= set(list_types(fork=fork, preset=preset))
    full = populated_block(fork, preset)
    blinded = copy.deepcopy(full)
    payload = blinded["body"].pop("execution_payload")
    header = {
        key: value for key, value in payload.items() if key not in {"transactions", "withdrawals"}
    }
    header["transactions_root"] = codec("Transactions").hash_tree_root(payload["transactions"])
    header["withdrawals_root"] = codec("Withdrawals").hash_tree_root(payload["withdrawals"])
    blinded["body"]["execution_payload_header"] = header
    assert codec("ExecutionPayload").hash_tree_root(payload) == codec(
        "ExecutionPayloadHeader"
    ).hash_tree_root(header)
    assert codec("BeaconBlockBody").hash_tree_root(full["body"]) == codec(
        "BlindedBeaconBlockBody"
    ).hash_tree_root(blinded["body"])
    assert codec("BeaconBlock").hash_tree_root(full) == codec("BlindedBeaconBlock").hash_tree_root(
        blinded
    )
    signature = b"\x88" * 96
    signed = {"message": full, "signature": signature}
    signed_blinded = {"message": blinded, "signature": signature}
    assert codec("SignedBeaconBlock").hash_tree_root(signed) == codec(
        "SignedBlindedBeaconBlock"
    ).hash_tree_root(signed_blinded)

    proofs = [b"\x99" * 48] * (128 if fork == "fulu" else 1)
    blobs = [b"\xab" * 131072]
    contents = {"block": full, "kzg_proofs": proofs, "blobs": blobs}
    signed_contents = {"signed_block": signed, "kzg_proofs": proofs, "blobs": blobs}
    values = {
        "BeaconBlockContents": contents,
        "SignedBeaconBlockContents": signed_contents,
        "BlindedBeaconBlockBody": blinded["body"],
        "BlindedBeaconBlock": blinded,
        "SignedBlindedBeaconBlock": signed_blinded,
    }
    for name, value in values.items():
        current = codec(name)
        encoded = current.serialize(value)
        assert current.deserialize(encoded) == value
        assert current.from_json(current.to_json(value)) == value
        assert current.loads(current.dumps(value)) == value
        assert current.hash_tree_root_from_ssz(encoded) == current.hash_tree_root(value)
    for name, block_name, block_value in [
        ("BeaconBlockContents", "BeaconBlock", full),
        ("SignedBeaconBlockContents", "SignedBeaconBlock", signed),
    ]:
        current = codec(name)
        schema = current.schema["fields"]
        proof_limit = 33554432 if fork == "fulu" else 4096
        assert schema["kzg_proofs"]["limit"] == proof_limit
        assert schema["blobs"]["limit"] == 4096
        expected = merkleize(
            [
                codec(block_name).hash_tree_root(block_value),
                composite_list_root(proofs, proof_limit),
                composite_list_root(blobs, 4096),
            ],
            3,
        )
        assert current.hash_tree_root(values[name]) == expected
        encoded = current.serialize(values[name])
        fixed = struct.pack(
            "<III",
            12,
            12 + len(codec(block_name).serialize(block_value)),
            12 + len(codec(block_name).serialize(block_value)) + len(proofs) * 48,
        )
        assert encoded[:12] == fixed


@pytest.mark.parametrize("preset", PRESETS)
def test_fulu_proof_limit_differs_from_electra(preset):
    proofs = [bytes(48)] * 4097
    fulu = get_type("BeaconBlockContents", fork="fulu", preset=preset)
    value = fulu.default()
    value["kzg_proofs"] = proofs
    assert fulu.deserialize(fulu.serialize(value)) == value
    with pytest.raises(SSZError, match="invalid list length"):
        get_type("BeaconBlockContents", fork="electra", preset=preset).serialize(value)


@pytest.mark.parametrize("fork", FORKS)
def test_contents_require_contents_fields_and_blinded_payload_header(fork):
    codec = get_type("BeaconBlockContents", fork=fork, preset="minimal")
    with pytest.raises(SSZError, match="missing fields"):
        codec.serialize({"block": populated_block(fork, "minimal")})
    with pytest.raises(SSZError, match="missing fields"):
        get_type("BlindedBeaconBlock", fork=fork, preset="minimal").serialize(
            populated_block(fork, "minimal")
        )
