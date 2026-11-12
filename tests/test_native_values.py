import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from ssz_z import FORKS, PRESETS, NativeValue, SSZError, get_type
from ssz_z._native import Operation


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", FORKS)
def test_block_fast_path(fork, preset):
    codec = get_type("BeaconBlock", fork=fork, preset=preset)
    value = codec.default()
    value["slot"], value["proposer_index"] = 77, 9
    if fork == "gloas":
        value["body"]["signed_execution_payload_bid"]["message"]["builder_index"] = 123
    encoded = codec.serialize(value)
    with codec.load_ssz(encoded) as native:
        assert native.to_ssz() is encoded
        assert native.slot == 77
        assert native.field("proposer_index") == 9
        assert native.field("state_root") == value["state_root"]
        if fork == "gloas":
            assert native.builder_index == 123
        expected_header = {key: item for key, item in value.items() if key != "body"}
        expected_header["body_root"] = get_type(
            "BeaconBlockBody", fork=fork, preset=preset
        ).hash_tree_root(value["body"])
        assert native.header_dict() == get_type(
            "BeaconBlockHeader", fork=fork, preset=preset
        ).to_json(expected_header)
        assert native.block_hash_tree_root() == codec.hash_tree_root(value)
        header = native.header_dict()
        header["slot"] = "bad"
        assert native.header_dict()["slot"] == "77"
        signed = native.sign("0x" + "11" * 96)
        expected_signed = {"message": value, "signature": b"\x11" * 96}
        assert signed.to_ssz() == signed.codec.serialize(expected_signed)
        assert signed.hash_tree_root() == signed.codec.hash_tree_root(expected_signed)
        assert signed.block_hash_tree_root() == native.block_hash_tree_root()
        assert signed.slot == 77
        assert codec.serialize(native) is encoded
        assert codec.to_json(native) == codec.to_json(value)
        assert codec.hash_tree_root(native) == codec.hash_tree_root(value)
    assert native.closed
    assert signed.to_obj() == expected_signed
    signed.close()


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", ["electra", "fulu"])
def test_blob_contents_fast_path(fork, preset):
    codec = get_type("BeaconBlockContents", fork=fork, preset=preset)
    value = codec.default()
    value["block"]["slot"] = 12
    value["block"]["body"]["blob_kzg_commitments"] = [b"\x33" * 48]
    value["blobs"] = [b"\x44" * 131072]
    value["kzg_proofs"] = [b"\x55" * 48] * (128 if fork == "fulu" else 1)
    with codec.load_obj(value) as native:
        assert native.slot == 12
        assert native.to_obj() == value
        root = native.block_hash_tree_root()
        signed = native.sign(b"\x66" * 96)
    expected = {
        "signed_block": {"message": value["block"], "signature": b"\x66" * 96},
        "blobs": value["blobs"],
        "kzg_proofs": value["kzg_proofs"],
    }
    with signed:
        assert signed.to_ssz() == signed.codec.serialize(expected)
        assert signed.hash_tree_root() == signed.codec.hash_tree_root(expected)
        assert signed.block_hash_tree_root() == root
        assert signed.to_obj() == expected
        assert json.loads(signed.to_json()) == signed.codec.to_json(expected)
        with codec.load_json(json.dumps(codec.to_json(value))) as reparsed:
            assert reparsed.to_ssz() == codec.serialize(value)


@pytest.mark.parametrize(
    "name", ["VoluntaryExit", "BeaconBlock", "ExecutionPayloadEnvelope", "ProposerPreferences"]
)
def test_sign_fixed_and_variable_values(name):
    codec = get_type(name, preset="minimal")
    with codec.load_obj(codec.default()) as native:
        # Cover cached roots as well as a wrapper created before hashing.
        for cached in (False, True):
            if cached:
                native.hash_tree_root()
            with native.sign(bytes(96)) as signed:
                assert signed.to_obj() == {"message": codec.default(), "signature": bytes(96)}
                assert signed.hash_tree_root() == signed.codec.hash_tree_root_from_ssz(
                    signed.to_ssz()
                )
    with pytest.raises((SSZError, ValueError)):
        get_type("Uint64").load_obj(1).sign(bytes(96))


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
        get_type("Checkpoint").load_json(text)


def test_native_json_order_escapes_and_rest():
    codec = get_type("Checkpoint")
    expected = {"epoch": 12, "root": bytes(32)}
    text = '{"root":"0x' + "00" * 32 + '","epo\\u0063h":"0012"}'
    with codec.load_json(text) as native:
        assert native.to_obj() == expected
    with codec.load_json(
        '{"other":[1,{"str":"a\\u0062"}],"data":' + text + ',"version":"fulu"}', wrapped=True
    ) as native:
        assert native.to_obj() == expected
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
    codec = get_type("Bytes4")
    for decode in (codec.from_json, lambda v: codec.load_json(json.dumps(v))):
        with pytest.raises(SSZError):
            decode(bad)


def test_input_snapshots_closed_values_and_type_checks():
    codec = get_type("Checkpoint")
    encoded = codec.serialize(codec.default())
    source = bytearray(encoded)
    native = codec.load_ssz(source)
    source[0] = 77
    assert native.to_ssz() == encoded
    snapshot = native.to_obj()
    snapshot["epoch"] = 1
    assert native.to_obj()["epoch"] == 0
    output = native.to_ssz()
    native.close()
    native.close()
    assert output == encoded
    for function in (
        native.to_ssz,
        native.to_obj,
        native.to_json,
        native.hash_tree_root,
        native.header_dict,
        native.block_hash_tree_root,
        lambda: native.field("epoch"),
        lambda: native.sign(bytes(96)),
        lambda: native.__enter__(),
    ):
        with pytest.raises(ValueError, match="closed"):
            function()
    with pytest.raises(SSZError):
        NativeValue(codec, b"bad")
    with codec.load_ssz(encoded) as native:
        with pytest.raises(ValueError, match="different type"):
            get_type("BeaconBlock").serialize(native)
        with pytest.raises(SSZError, match="NotABlock"):
            native.header_dict()
        with pytest.raises(TypeError):
            native.field(1)
        with pytest.raises(ValueError):
            native.field("missing")
    block = get_type("BeaconBlock", preset="minimal").load_obj(
        get_type("BeaconBlock", preset="minimal").default()
    )
    for signature in (bytes(95), bytes(97), "0x" + "gg" * 96, "0x" + "00 " * 96):
        with pytest.raises(SSZError):
            block.sign(signature)
    block.close()


def test_native_concurrent_read_sign_and_close():
    codec = get_type("BeaconBlock", preset="minimal")
    encoded = codec.serialize(codec.default())
    native = codec.load_ssz(encoded)
    expected = native.hash_tree_root()

    def work(index):
        if index == 39:
            native.close()
            return
        try:
            assert native.to_ssz() == encoded
            assert native.hash_tree_root() == expected
            with native.sign(bytes(96)) as signed:
                assert signed.codec.deserialize(signed.to_ssz())["message"] == codec.default()
        except ValueError as error:
            assert str(error) == "SSZ value is closed"

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(work, range(40)))
    assert native.closed


def test_proposal_does_not_repeat_native_operations(monkeypatch):
    from ssz_z import value as implementation

    codec = get_type("BeaconBlockContents", fork="fulu", preset="minimal")
    _ = codec._signed_codec  # Resolve metadata outside the operation-count assertion.
    data = codec.serialize(codec.default())
    calls = []
    original = implementation.call

    def counted(preset, fork, name, operation, data=b""):
        calls.append(operation)
        return original(preset, fork, name, operation, data)

    monkeypatch.setattr(implementation, "call", counted)
    with codec.load_ssz(data) as value:
        value.header_dict()
        with value.sign(bytes(96)) as signed:
            signed.to_ssz()
        value.block_hash_tree_root()
        value.header_dict()
        assert value.slot == 0
    assert calls == [
        Operation.VALIDATE_SSZ,
        Operation.BLOCK_PROJECTION,
    ]  # One validation, one body hash; signing/encoding reuse bytes.


@pytest.mark.parametrize("fork", FORKS)
def test_native_nested_json_order_and_binary_bits(fork):
    def reverse(value):
        if isinstance(value, dict):
            return {key: reverse(item) for key, item in reversed(value.items())}
        if isinstance(value, list):
            return [reverse(item) for item in value]
        return value

    codec = get_type("BeaconBlock", fork=fork, preset="minimal")
    value = codec.default()
    json_value = codec.to_json(value)
    with codec.load_json(json.dumps(reverse(json_value))) as native:
        assert native.to_obj() == value
    attestation = get_type("Attestation", fork=fork, preset="minimal")
    value = attestation.to_json(attestation.default())
    value["aggregation_bits"] = "0x00"
    with pytest.raises(SSZError):
        attestation.load_json(json.dumps(value))


def test_native_failure_after_partial_allocation():
    codec = get_type("ExecutionPayload", preset="minimal")
    value = codec.to_json(codec.default())
    # Decode several allocated lists before a late invalid field.
    value["transactions"] = ["0x010203"] * 32
    value["slot_number"] = "bad"
    text = json.dumps(value)
    for _ in range(100):
        with pytest.raises(SSZError):
            codec.load_json(text)
    good = codec.dumps(codec.default())
    assert codec.load_json(good).to_ssz() == codec.serialize(codec.default())
