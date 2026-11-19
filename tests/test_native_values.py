import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from ssz_z import FORKS, PRESETS, NativeValue, SSZError, get_type
from ssz_z._native import Operation
from ssz_z.beacon_api import BlockValue
from tests.json_helpers import json_document, json_value


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", FORKS)
def test_block_fast_path(fork, preset):
    codec = get_type("BeaconBlock", fork=fork, preset=preset)
    value = json.loads(codec.default().to_json())
    (value["slot"], value["proposer_index"]) = (77, 9)
    if fork == "gloas":
        value["body"]["signed_execution_payload_bid"]["message"]["builder_index"] = 123
    encoded = codec.load_json(json_document(value)).to_ssz()
    native = BlockValue(codec.load_ssz(encoded))
    assert native.value.to_ssz() is encoded
    assert native.slot == 77
    assert native.value.field("proposer_index") == 9
    assert native.value.field("state_root") == bytes.fromhex(value["state_root"][2:])
    if fork == "gloas":
        assert native.builder_index == 123
    expected_header = {key: item for (key, item) in value.items() if key != "body"}
    expected_header["body_root"] = (
        get_type("BeaconBlockBody", fork=fork, preset=preset)
        .load_json(json_document(value["body"]))
        .hash_tree_root()
    )
    assert native.header_dict() == json_value(expected_header)
    assert native.block_hash_tree_root() == codec.load_json(json_document(value)).hash_tree_root()
    header = native.header_dict()
    header["slot"] = "bad"
    assert native.header_dict()["slot"] == "77"
    signed = native.sign("0x" + "11" * 96)
    expected_signed = {"message": value, "signature": b"\x11" * 96}
    assert (
        signed.value.to_ssz()
        == signed.value.codec.load_json(json_document(expected_signed)).to_ssz()
    )
    assert (
        signed.value.hash_tree_root()
        == signed.value.codec.load_json(json_document(expected_signed)).hash_tree_root()
    )
    assert signed.block_hash_tree_root() == native.block_hash_tree_root()
    assert signed.slot == 77
    assert codec.load_ssz(native.value.to_ssz()) == native.value
    assert json.loads(native.value.to_json()) == json_value(value)
    assert json.loads(signed.value.to_json()) == json_value(expected_signed)


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", ["electra", "fulu"])
def test_blob_contents_fast_path(fork, preset):
    codec = get_type("BeaconBlockContents", fork=fork, preset=preset)
    value = json.loads(codec.default().to_json())
    value["block"]["slot"] = 12
    value["block"]["body"]["blob_kzg_commitments"] = [b"3" * 48]
    value["blobs"] = [b"D" * 131072]
    value["kzg_proofs"] = [b"U" * 48] * (128 if fork == "fulu" else 1)
    native = BlockValue(codec.load_json(json_document(value)))
    assert native.slot == 12
    assert json.loads(native.value.to_json()) == json_value(value)
    root = native.block_hash_tree_root()
    signed = native.sign(b"f" * 96)
    expected = {
        "signed_block": {"message": value["block"], "signature": b"f" * 96},
        "blobs": value["blobs"],
        "kzg_proofs": value["kzg_proofs"],
    }
    assert signed.value.to_ssz() == signed.value.codec.load_json(json_document(expected)).to_ssz()
    assert (
        signed.value.hash_tree_root()
        == signed.value.codec.load_json(json_document(expected)).hash_tree_root()
    )
    assert signed.block_hash_tree_root() == root
    assert json.loads(signed.value.to_json()) == json_value(expected)
    assert json.loads(signed.value.to_json()) == json_value(expected)
    reparsed = codec.load_json(json_document(json_value(value)))
    assert reparsed.to_ssz() == codec.load_json(json_document(value)).to_ssz()


@pytest.mark.parametrize(
    "name", ["VoluntaryExit", "BeaconBlock", "ExecutionPayloadEnvelope", "ProposerPreferences"]
)
@pytest.mark.parametrize("signature", [bytes(96), bytes(range(96))])
def test_sign_fixed_and_variable_values(name, signature):
    codec = get_type(name, preset="minimal", fork="gloas")
    native = codec.default()
    # Exercise signing both before and after caching the unsigned root.
    for cached in (False, True):
        if cached:
            native.hash_tree_root()
        signed = native.sign(signature)
        assert json.loads(signed.to_json()) == json_value(
            {"message": json.loads(codec.default().to_json()), "signature": signature}
        )
        assert (signed._root is not None) == cached
        assert signed.hash_tree_root() == signed.codec.hash_tree_root_from_ssz(signed.to_ssz())
    with pytest.raises((SSZError, ValueError)):
        get_type("Uint64", fork="primitive", preset="mainnet").load_json(json_document(1)).sign(
            bytes(96)
        )


@pytest.mark.parametrize(
    "text",
    [
        b"",
        b"null",
        b"{}",
        b'{"epoch":"0"}',
        b'{"epoch":"0","root":"0x"}',
        b'{"epoch":"0","epoch":"1","root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":"0","extra":1,"root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":true,"root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":"-1","root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":"+1","root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":1.0,"root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":"1_0","root":"0x' + b"00" * 32 + b'"}',
        b'{"epoch":"18446744073709551616","root":"0x' + b"00" * 32 + b'"}',
    ],
)
def test_native_json_rejects_invalid_values(text):
    with pytest.raises(SSZError):
        get_type("Checkpoint", fork="gloas", preset="mainnet").load_json(text)


def test_native_json_order_escapes_and_rest():
    codec = get_type("Checkpoint", fork="gloas", preset="mainnet")
    expected = {"epoch": 12, "root": bytes(32)}
    text = '{"root":"0x' + "00" * 32 + '","epo\\u0063h":"0012"}'
    native = codec.load_json(text)
    assert json.loads(native.to_json()) == json_value(expected)
    native = codec.load_json(
        '{"other":[1,{"str":"a\\u0062"}],"data":' + text + ',"version":"fulu"}', wrapped=True
    )
    assert json.loads(native.to_json()) == json_value(expected)
    for invalid in [
        '{"data":' + text + ',"data":' + text + "}",
        '{"foo":1}',
        '{"data":' + text + "} null",
    ]:
        with pytest.raises(SSZError):
            codec.load_json(invalid, wrapped=True)
    duplicate = '{"root":"0x' + "00" * 32 + '","epoch":1,"epo\\u0063h":2}'
    with pytest.raises(SSZError, match="DuplicateField"):
        codec.load_json(duplicate)


@pytest.mark.parametrize(
    "bad", ["", "0x", "0x0", "0xzz", "0x00 00", "00000000", "0X00000000", "0x００００００００"]
)
def test_hex_validation_all_paths(bad):
    codec = get_type("Bytes4", fork="primitive", preset="mainnet")
    with pytest.raises(SSZError):
        codec.load_json(json.dumps(bad))


def test_input_snapshots_and_type_checks():
    codec = get_type("Checkpoint", fork="gloas", preset="mainnet")
    encoded = codec.default().to_ssz()
    source = bytearray(encoded)
    native = codec.load_ssz(source)
    source[0] = 77
    assert native.to_ssz() == encoded
    snapshot = json.loads(native.to_json())
    snapshot["epoch"] = 1
    assert json.loads(native.to_json())["epoch"] == json_value(0)
    output = native.to_ssz()
    with pytest.raises(FrozenInstanceError):
        native._ssz = b"changed"
    with pytest.raises(FrozenInstanceError):
        native.codec = get_type("Uint64", fork="primitive", preset="mainnet")
    del native
    assert output == encoded
    with pytest.raises(SSZError):
        NativeValue(codec, b"bad")
    native = codec.load_ssz(encoded)
    with pytest.raises(TypeError):
        get_type("BeaconBlock", fork="gloas", preset="mainnet").load_json(native)
    with pytest.raises(ValueError, match="not a block"):
        BlockValue(native)
    with pytest.raises(TypeError):
        native.field(1)
    with pytest.raises(ValueError):
        native.field("missing")
    block = get_type("BeaconBlock", preset="minimal", fork="gloas").load_json(
        json_document(
            json.loads(get_type("BeaconBlock", preset="minimal", fork="gloas").default().to_json())
        )
    )
    for signature in (bytes(95), bytes(97), "0x" + "gg" * 96, "0x" + "00 " * 96):
        with pytest.raises(SSZError):
            block.sign(signature)


def test_native_concurrent_read_and_sign():
    codec = get_type("BeaconBlock", preset="minimal", fork="gloas")
    expected_obj = json.loads(codec.default().to_json())
    encoded = codec.load_json(json_document(expected_obj)).to_ssz()
    native = codec.load_ssz(encoded)
    expected = codec.load_json(json_document(expected_obj)).hash_tree_root()

    def work(index):
        assert native.to_ssz() is encoded
        assert native.hash_tree_root() == expected
        assert BlockValue(native).header_dict()["slot"] == "0"
        signed = native.sign(bytes([index]) * 96)
        assert json.loads(signed.to_json()) == json_value(
            {"message": expected_obj, "signature": bytes([index]) * 96}
        )
        assert signed.hash_tree_root() == signed.codec.hash_tree_root_from_ssz(signed.to_ssz())

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(work, range(40)))


def test_proposal_does_not_repeat_native_operations(monkeypatch):
    from ssz_z import types as implementation

    codec = get_type("BeaconBlockContents", fork="fulu", preset="minimal")
    _ = get_type("SignedBeaconBlockContents", fork="fulu", preset="minimal")
    data = codec.default().to_ssz()
    calls = []
    original = implementation.call

    def counted(preset, fork, name, operation, data=b""):
        calls.append(operation)
        return original(preset, fork, name, operation, data)

    monkeypatch.setattr(implementation, "call", counted)
    value = BlockValue(codec.load_ssz(data))
    value.header_dict()
    signed = value.sign(bytes(96))
    signed.value.to_ssz()
    value.block_hash_tree_root()
    value.header_dict()
    assert value.slot == 0
    # One validation and one body hash; signing and projections reuse SSZ bytes.
    assert calls == [Operation.VALIDATE_SSZ, Operation.BLOCK_PROJECTION]


def test_contents_signature_and_output_boundaries(monkeypatch):
    from ssz_z import value as implementation

    codec = get_type("BeaconBlockContents", fork="fulu", preset="minimal")
    original = codec.default().to_ssz()
    proposal = BlockValue(codec.load_ssz(original))
    for signature in (bytes(95), bytes(97), "0x" + "gg" * 96):
        with pytest.raises(SSZError):
            proposal.sign(signature)
    monkeypatch.setattr(implementation, "MAX_INPUT_SIZE", len(original) + 50)
    with pytest.raises(SSZError, match="exceeds"):
        proposal.sign(bytes(96))
    assert proposal.value.to_ssz() == original


@pytest.mark.parametrize("fork", FORKS)
def test_native_nested_json_order_and_binary_bits(fork):

    def reverse(value):
        if isinstance(value, dict):
            return {key: reverse(item) for (key, item) in reversed(value.items())}
        if isinstance(value, list):
            return [reverse(item) for item in value]
        return value

    codec = get_type("BeaconBlock", fork=fork, preset="minimal")
    value = json.loads(codec.default().to_json())
    native = codec.load_json(json_document(reverse(value)))
    assert json.loads(native.to_json()) == json_value(value)
    attestation = get_type("Attestation", fork=fork, preset="minimal")
    value = json_value(json.loads(attestation.default().to_json()))
    value["aggregation_bits"] = "0x00"
    with pytest.raises(SSZError):
        attestation.load_json(json_document(value))


def test_native_failure_after_partial_allocation():
    codec = get_type("ExecutionPayload", preset="minimal", fork="gloas")
    value = json_value(json.loads(codec.default().to_json()))
    value["transactions"] = ["0x010203"] * 32
    value["slot_number"] = "bad"
    text = json_document(value)
    for _ in range(100):
        with pytest.raises(SSZError):
            codec.load_json(text)
    good = json_document(json.loads(codec.default().to_json()))
    assert codec.load_json(good).to_ssz() == codec.default().to_ssz()


@pytest.mark.parametrize(
    "name,value,expected_json",
    [
        ("Transaction", b"\x01\xff", "0x01ff"),
        ("BlockAccessList", b"\x01\xff", "0x01ff"),
        ("EpochParticipation", [1, 255], ["1", "255"]),
    ],
)
def test_progressive_bytes_and_uint8_lists_have_distinct_json(name, value, expected_json):
    codec = get_type(name, fork="gloas", preset="mainnet")
    assert codec.load_json(json_document(value)).to_ssz() == b"\x01\xff"
    assert json_value(value) == expected_json
    assert json.loads(codec.load_json(json_document(expected_json)).to_json()) == json_value(value)
    native = codec.load_json(json_document(expected_json))
    assert native.to_ssz() == b"\x01\xff"
    assert json.loads(native.to_json()) == json_value(value)
    assert json.loads(native.to_json()) == expected_json
    wrong_shape = ["1", "255"] if isinstance(expected_json, str) else "0x01ff"
    with pytest.raises(SSZError):
        codec.load_json(json_document(wrong_shape))


def test_default_uses_one_native_ssz_operation(monkeypatch):
    from ssz_z import types as implementation
    from ssz_z._native import Operation

    codec = get_type("BeaconState", fork="gloas", preset="minimal")
    original = implementation.call
    calls = []

    def counted(preset, fork, name, operation, data=b""):
        calls.append(operation)
        return original(preset, fork, name, operation, data)

    monkeypatch.setattr(implementation, "call", counted)
    value = codec.default()
    assert calls == [Operation.DEFAULT_SSZ]
    assert codec.load_json(value.to_json()) == value


def test_sign_reuses_cached_root_without_native_calls(monkeypatch):
    from ssz_z import types as implementation

    codec = get_type("BeaconBlock", fork="gloas", preset="minimal")
    value = codec.default()
    original_root = value.hash_tree_root()
    signature = bytes(range(96))
    target = codec._signed_codec
    expected = target.load_json(
        json_document(
            {
                "message": json.loads(value.to_json()),
                "signature": signature,
            }
        )
    ).hash_tree_root()

    def unexpected_call(*args, **kwargs):
        pytest.fail("Signing with a cached root must not require native calls")

    monkeypatch.setattr(implementation, "call", unexpected_call)
    signed = value.sign(signature)
    assert signed.hash_tree_root() == expected
    assert value.hash_tree_root() == original_root
