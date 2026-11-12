import hashlib
import json
import struct
from concurrent.futures import ThreadPoolExecutor

import pytest

from ssz_z import FORKS, PRESETS, SSZError, get_type, list_types


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", FORKS)
def test_requested_forks_and_presets(preset, fork):
    names = list_types(fork=fork, preset=preset)
    assert {
        "BeaconState",
        "BeaconBlock",
        "SignedBeaconBlock",
        "Attestation",
        "BlobKZGCommitments",
        "BLSToExecutionChanges",
        "BlockRoots",
        "StateRoots",
    } <= set(names)
    legacy_names = {
        "BlobKzgCommitments",
        "SignedBLSToExecutionChanges",
        "HistoricalBlockRoots",
        "HistoricalStateRoots",
        "PtcWindow",
    }
    assert not legacy_names.intersection(names)
    for name in legacy_names:
        with pytest.raises(ValueError, match="Unknown SSZ type"):
            get_type(name, fork=fork, preset=preset)
    for name in names:
        codec = get_type(name, fork=fork, preset=preset)
        value = codec.default()
        serialized = codec.serialize(value)
        assert codec.deserialize(serialized) == value, name
        assert codec.from_json(codec.to_json(value)) == value, name
        assert codec.hash_tree_root(value) == codec.hash_tree_root_from_ssz(serialized), name


@pytest.mark.parametrize("bits", [8, 16, 32, 64, 128, 256])
@pytest.mark.parametrize("preset", PRESETS)
def test_unsigned_integers(bits, preset):
    codec = get_type(f"Uint{bits}", preset=preset)
    for value in [0, 1, (1 << bits) - 1]:
        encoded = value.to_bytes(bits // 8, "little")
        assert codec.serialize(value) == encoded
        assert codec.deserialize(encoded) == value
        assert codec.hash_tree_root(value) == encoded.ljust(32, b"\0")
        assert codec.from_json(json.dumps(str(value))) == value
        assert codec.to_json(value) == str(value)
    for value in [-1, 1 << bits, True, 1.0, "-1", "+1", " 1", "1_0"]:
        with pytest.raises(SSZError):
            codec.serialize(value)


def test_known_checkpoint_root_and_unordered_json():
    codec = get_type("Checkpoint")
    root = b"\x12" * 32
    value = {"root": root, "epoch": 123}
    expected = hashlib.sha256((123).to_bytes(32, "little") + root).digest()
    assert codec.hash_tree_root(value) == expected
    assert codec.loads('{"root":"0x' + root.hex() + '","epoch":"123"}') == value
    assert json.loads(codec.dumps(value)) == {"epoch": "123", "root": "0x" + root.hex()}


@pytest.mark.parametrize(
    "value",
    [{}, {"epoch": 0, "root": b"\0" * 32, "extra": 0}, {"epoch": 0, "root": b"short"}, None],
)
def test_bad_container(value):
    with pytest.raises(SSZError):
        get_type("Checkpoint").serialize(value)


@pytest.mark.parametrize(
    "text", ["{", '{"epoch":"1","epoch":"2","root":"0x"}', "null trailing", "[NaN]"]
)
def test_bad_json(text):
    with pytest.raises(SSZError):
        get_type("Checkpoint").from_json(text)


def test_invalid_binary_inputs():
    boolean = get_type("Boolean")
    for data in [b"", b"\x02", b"\x00\x00"]:
        for operation in [boolean.deserialize, boolean.hash_tree_root_from_ssz]:
            with pytest.raises(SSZError):
                operation(data)
    codec = get_type("SignedBeaconBlock", preset="minimal")
    serialized = codec.serialize(codec.default())
    invalid = [
        serialized[:99],
        b"\0" * len(serialized),
        struct.pack("<I", 99) + serialized[4:],
        struct.pack("<I", len(serialized) + 1) + serialized[4:],
    ]
    for data in invalid:
        for operation in [codec.deserialize, codec.hash_tree_root_from_ssz]:
            with pytest.raises(SSZError):
                operation(data)


def test_preset_specific_types():
    lengths = {}
    for preset in PRESETS:
        codec = get_type("BeaconState", fork="fulu", preset=preset)
        lengths[preset] = len(codec.default()["proposer_lookahead"])
    assert lengths == {"mainnet": 64, "minimal": 16, "gnosis": 32}
    assert (
        get_type("PayloadAttestation", preset="minimal").schema["fields"]["aggregation_bits"][
            "length"
        ]
        == 16
    )
    assert (
        get_type("PayloadAttestation", preset="gnosis").schema["fields"]["aggregation_bits"][
            "length"
        ]
        == 512
    )


def test_bitfield_bounds():
    codec = get_type("Attestation", fork="electra", preset="minimal")
    value = codec.default()
    for bits in [b"", b"\0", b"\x01\0", b"\0" * 1025 + b"\x01"]:
        value["aggregation_bits"] = bits
        with pytest.raises(SSZError):
            codec.serialize(value)
    payload = get_type("PayloadAttestation", preset="minimal")
    value = payload.default()
    value["aggregation_bits"] = b"\x00\x00\x01"
    with pytest.raises(SSZError):
        payload.serialize(value)


def test_names_and_independent_defaults():
    for kwargs in [{"fork": "unknown"}, {"preset": "unknown"}]:
        with pytest.raises(ValueError):
            get_type("BeaconState", **kwargs)
    with pytest.raises(ValueError):
        get_type("not_a_type")
    codec = get_type("Checkpoint")
    value = codec.default()
    value["epoch"] = 1
    assert codec.default()["epoch"] == 0
    schema = codec.schema
    schema["fields"].clear()
    assert codec.schema["fields"]
    with pytest.raises(TypeError):
        codec.deserialize(16)


def test_concurrent_native_calls():
    def work(index):
        preset = PRESETS[index % len(PRESETS)]
        codec = get_type("BeaconBlock", preset=preset)
        value = codec.default()
        value["slot"] = index
        for _ in range(4):
            assert codec.deserialize(codec.serialize(value)) == value
            assert len(codec.hash_tree_root(value)) == 32

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(work, range(36)))


def test_progressive_gloas_schemas():
    assert get_type("BeaconState", fork="gloas").schema["progressive"]
    assert get_type("ExecutionRequests").schema["fields"]["deposits"]["progressive"]
    gloas = get_type("Attestation", preset="minimal")
    electra = get_type("Attestation", fork="electra", preset="minimal")
    value = gloas.default()
    assert gloas.serialize(value) == electra.serialize(value)
    assert gloas.hash_tree_root(value) != electra.hash_tree_root(value)
    value["aggregation_bits"] = b"\0" * 1025 + b"\x01"
    assert gloas.deserialize(gloas.serialize(value)) == value
    with pytest.raises(SSZError):
        electra.serialize(value)


def test_scalar_json_documents():
    codec = get_type("Uint64")
    assert codec.from_json("001") == 1
    assert codec.loads('"001"') == 1
    with pytest.raises(SSZError):
        codec.loads("001")
    byte = get_type("Bytes4")
    assert byte.from_json("0x01020304") == b"\x01\x02\x03\x04"
    assert byte.loads('"0x01020304"') == b"\x01\x02\x03\x04"
    with pytest.raises(SSZError):
        byte.loads("0x01020304")


@pytest.mark.parametrize("fork", FORKS)
def test_ssz_mutations_are_rejected_or_round_trip(fork):
    import random

    codec = get_type("SignedBeaconBlock", fork=fork, preset="minimal")
    original = codec.serialize(codec.default())
    random_source = random.Random(20261016)
    for _ in range(100):
        candidate = bytearray(original)
        for _ in range(random_source.randrange(1, 5)):
            index = random_source.randrange(len(candidate))
            candidate[index] = random_source.randrange(256)
        if random_source.randrange(2):
            candidate = candidate[: random_source.randrange(len(candidate))]
        data = bytes(candidate)
        try:
            value = codec.deserialize(data)
        except SSZError:
            with pytest.raises(SSZError):
                codec.hash_tree_root_from_ssz(data)
        else:
            assert codec.serialize(value) == data
            assert codec.hash_tree_root(value) == codec.hash_tree_root_from_ssz(data)
