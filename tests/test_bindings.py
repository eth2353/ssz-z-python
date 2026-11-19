import hashlib
import json
import random
import struct
from concurrent.futures import ThreadPoolExecutor

import pytest

from ssz_z import FORKS, PRESETS, NativeValue, SSZError, get_type, list_types
from tests.json_helpers import json_document


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
    for name in {
        "BlobKzgCommitments",
        "SignedBLSToExecutionChanges",
        "HistoricalBlockRoots",
        "HistoricalStateRoots",
        "PtcWindow",
    }:
        assert name not in names
        with pytest.raises(ValueError, match="Unknown SSZ type"):
            get_type(name, fork=fork, preset=preset)
    for name in names:
        codec = get_type(name, fork=fork, preset=preset)
        value = codec.default()
        assert isinstance(value, NativeValue)
        assert codec.load_ssz(value.to_ssz()) == value, name
        assert codec.load_json(value.to_json()) == value, name
        assert value.hash_tree_root() == codec.hash_tree_root_from_ssz(value.to_ssz()), name


@pytest.mark.parametrize("bits", [8, 16, 32, 64, 128, 256])
@pytest.mark.parametrize("preset", PRESETS)
def test_unsigned_integers(bits, preset):
    codec = get_type(f"Uint{bits}", preset=preset, fork="primitive")
    for number in [0, 1, (1 << bits) - 1]:
        encoded = number.to_bytes(bits // 8, "little")
        value = codec.load_json(json.dumps(str(number)))
        assert value.to_ssz() == encoded
        assert value.to_json() == f'"{number}"'.encode()
        assert value.hash_tree_root() == encoded.ljust(32, b"\0")
        assert codec.load_ssz(encoded) == value
    for invalid in [-1, 1 << bits, True, 1.0, "-1", "+1", " 1", "1_0"]:
        with pytest.raises(SSZError):
            codec.load_json(json.dumps(invalid))


def test_known_checkpoint_root_and_unordered_json():
    codec = get_type("Checkpoint", fork="gloas", preset="mainnet")
    root = b"\x12" * 32
    value = codec.load_json('{"root":"0x' + root.hex() + '","epoch":"123"}')
    assert value.hash_tree_root() == hashlib.sha256((123).to_bytes(32, "little") + root).digest()
    assert json.loads(value.to_json()) == {"epoch": "123", "root": "0x" + root.hex()}


@pytest.mark.parametrize(
    "value", [{}, {"epoch": 0, "root": bytes(32), "extra": 0}, {"epoch": 0, "root": b"short"}, None]
)
def test_bad_container(value):
    with pytest.raises(SSZError):
        get_type("Checkpoint", fork="gloas", preset="mainnet").load_json(json_document(value))


@pytest.mark.parametrize(
    "text", ["{", '{"epoch":"1","epoch":"2","root":"0x"}', "null trailing", "[NaN]"]
)
def test_bad_json(text):
    with pytest.raises(SSZError):
        get_type("Checkpoint", fork="gloas", preset="mainnet").load_json(text)


def test_invalid_binary_inputs():
    boolean = get_type("Boolean", fork="primitive", preset="mainnet")
    for data in [b"", b"\x02", b"\x00\x00"]:
        for operation in [boolean.load_ssz, boolean.hash_tree_root_from_ssz]:
            with pytest.raises(SSZError):
                operation(data)
    codec = get_type("SignedBeaconBlock", preset="minimal", fork="gloas")
    serialized = codec.default().to_ssz()
    for data in [
        serialized[:99],
        bytes(len(serialized)),
        struct.pack("<I", 99) + serialized[4:],
        struct.pack("<I", len(serialized) + 1) + serialized[4:],
    ]:
        for operation in [codec.load_ssz, codec.hash_tree_root_from_ssz]:
            with pytest.raises(SSZError):
                operation(data)


def test_preset_specific_types():
    lengths = {
        p: get_type("BeaconState", fork="fulu", preset=p).schema["fields"]["proposer_lookahead"][
            "length"
        ]
        for p in PRESETS
    }
    assert lengths == {"mainnet": 64, "minimal": 16, "gnosis": 32}
    for preset, size in [("minimal", 16), ("gnosis", 512)]:
        assert (
            get_type("PayloadAttestation", preset=preset, fork="gloas").schema["fields"][
                "aggregation_bits"
            ]["length"]
            == size
        )


def test_bitfield_bounds():
    codec = get_type("Attestation", fork="electra", preset="minimal")
    value = json.loads(codec.default().to_json())
    for bits in [b"", b"\0", b"\x01\0", bytes(1025) + b"\x01"]:
        value["aggregation_bits"] = "0x" + bits.hex()
        with pytest.raises(SSZError):
            codec.load_json(json.dumps(value))
    codec = get_type("PayloadAttestation", preset="minimal", fork="gloas")
    value = json.loads(codec.default().to_json())
    value["aggregation_bits"] = "0x000001"
    with pytest.raises(SSZError):
        codec.load_json(json.dumps(value))


def test_names_and_independent_defaults():
    for kwargs in [
        {"fork": "unknown", "preset": "mainnet"},
        {"fork": "gloas", "preset": "unknown"},
    ]:
        with pytest.raises(ValueError):
            get_type("BeaconState", **kwargs)
    with pytest.raises(ValueError):
        get_type("not_a_type", fork="gloas", preset="mainnet")
    codec = get_type("Checkpoint", fork="gloas", preset="mainnet")
    assert codec.default().field("epoch") == 0
    schema = codec.schema
    schema["fields"].clear()
    assert codec.schema["fields"]
    with pytest.raises(TypeError):
        codec.load_ssz(16)


def test_concurrent_native_calls():
    def work(index):
        codec = get_type("BeaconBlock", preset=PRESETS[index % len(PRESETS)], fork="gloas")
        document = json.loads(codec.default().to_json())
        document["slot"] = str(index)
        for _ in range(4):
            value = codec.load_json(json.dumps(document))
            assert codec.load_ssz(value.to_ssz()) == value
            assert value.field("slot") == index
            assert len(value.hash_tree_root()) == 32

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(work, range(36)))


def test_progressive_gloas_schemas():
    assert get_type("BeaconState", fork="gloas", preset="mainnet").schema["progressive"]
    assert get_type("ExecutionRequests", fork="gloas", preset="mainnet").schema["fields"][
        "deposits"
    ]["progressive"]
    gloas = get_type("Attestation", preset="minimal", fork="gloas")
    electra = get_type("Attestation", fork="electra", preset="minimal")
    assert gloas.default().to_ssz() == electra.default().to_ssz()
    assert gloas.default().hash_tree_root() != electra.default().hash_tree_root()
    document = json.loads(gloas.default().to_json())
    document["aggregation_bits"] = "0x" + (bytes(1025) + b"\x01").hex()
    encoded = json.dumps(document)
    assert json.loads(gloas.load_json(encoded).to_json()) == document
    with pytest.raises(SSZError):
        electra.load_json(encoded)


def test_json_input_is_always_a_document():
    codec = get_type("Uint64", fork="primitive", preset="mainnet")
    assert codec.load_json('"001"').to_json() == b'"1"'
    for text in ["001", "-0", "+1"]:
        with pytest.raises(SSZError):
            codec.load_json(text)
    byte = get_type("Bytes4", fork="primitive", preset="mainnet")
    assert byte.load_json('"0x01020304"').to_ssz() == b"\x01\x02\x03\x04"
    with pytest.raises(SSZError):
        byte.load_json("0x01020304")
    for value in [1, True, {}, [], None]:
        with pytest.raises(TypeError):
            codec.load_json(value)
    for text in ['"123"', b'"123"', bytearray(b'"123"'), memoryview(b'"123"')]:
        value = codec.load_json(text)
        assert isinstance(value.to_json(), bytes)
        assert isinstance(value.to_ssz(), bytes)
        assert value.to_ssz() == (123).to_bytes(8, "little")


@pytest.mark.parametrize("fork", FORKS)
def test_ssz_mutations_are_rejected_or_round_trip(fork):
    codec = get_type("SignedBeaconBlock", fork=fork, preset="minimal")
    original = codec.default().to_ssz()
    random_source = random.Random(20261016)
    for _ in range(100):
        candidate = bytearray(original)
        for _ in range(random_source.randrange(1, 5)):
            candidate[random_source.randrange(len(candidate))] = random_source.randrange(256)
        if random_source.randrange(2):
            candidate = candidate[: random_source.randrange(len(candidate))]
        data = bytes(candidate)
        try:
            value = codec.load_ssz(data)
        except SSZError:
            with pytest.raises(SSZError):
                codec.hash_tree_root_from_ssz(data)
        else:
            assert value.to_ssz() == data
            assert codec.load_json(value.to_json()).to_ssz() == data
            assert value.hash_tree_root() == codec.hash_tree_root_from_ssz(data)


def test_object_conversion_api_is_removed():
    codec = get_type("Checkpoint", fork="gloas", preset="mainnet")
    for name in (
        "load_obj",
        "serialize",
        "deserialize",
        "from_json",
        "to_json",
        "loads",
        "dumps",
        "hash_tree_root",
    ):
        assert not hasattr(codec, name)
    value = codec.default()
    for name in ("to_obj", "to_json_value"):
        assert not hasattr(value, name)


@pytest.mark.parametrize("text,expected", [(b"true", b"\x01"), (b"false", b"\x00")])
def test_json_boolean_literals(text, expected):
    value = get_type("Boolean", fork="primitive", preset="mainnet").load_json(text)
    assert value.to_ssz() == expected
    assert value.to_json() == text


@pytest.mark.parametrize(
    "text", [b'"true"', b'"false"', b"True", b"False", b"TRUE", b"FALSE", b"1", b"0", b"null"]
)
def test_json_booleans_reject_other_representations(text):
    with pytest.raises(SSZError):
        get_type("Boolean", fork="primitive", preset="mainnet").load_json(text)


def test_fork_must_be_explicit():
    with pytest.raises(TypeError, match="fork"):
        get_type("BeaconBlock", preset="mainnet")
    with pytest.raises(TypeError, match="fork"):
        get_type("Uint64", preset="mainnet")
    with pytest.raises(TypeError, match="fork"):
        list_types(preset="mainnet")
    assert get_type("Uint64", fork="primitive", preset="mainnet").load_json('"1"').to_ssz() == (
        1
    ).to_bytes(8, "little")


@pytest.mark.parametrize("name", ["BeaconBlock", "Uint64"])
def test_preset_must_be_explicit(name):
    with pytest.raises(TypeError, match="preset"):
        get_type(name, fork="gloas")
    with pytest.raises(TypeError, match="preset"):
        list_types(fork="gloas")


@pytest.mark.parametrize("preset", PRESETS)
def test_concurrent_first_hash_in_fresh_process(preset):
    # Loading schemas/defaults does not hash. Every worker reaches its first
    # native hash together.
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-c", """
import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from ssz_z import get_type
import sys

preset = sys.argv[1]
codec = get_type("Checkpoint", fork="gloas", preset=preset)
value = codec.default()
barrier = Barrier(16)
expected = hashlib.sha256(bytes(64)).digest()
def hash_once(_):
    barrier.wait()
    return codec.hash_tree_root_from_ssz(value.to_ssz())
with ThreadPoolExecutor(max_workers=16) as pool:
    assert all(root == expected for root in pool.map(hash_once, range(16)))
""", preset],
        check=True,
        timeout=30,
    )
