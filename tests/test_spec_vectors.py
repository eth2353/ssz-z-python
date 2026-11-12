"""Official release vectors. Set SSZ_SPEC_TESTS to an extracted tests directory."""

import json
import os
from pathlib import Path

import pytest
import snappy
import yaml

from ssz_z import FORKS, get_type

ROOT = Path(os.environ.get("SSZ_SPEC_TESTS", "fixtures/tests"))
BUNDLED = Path(__file__).parent / "vectors"
CASES = sorted(
    {
        *BUNDLED.glob("*/*/ssz_static/*/*/*/serialized.ssz_snappy"),
        *ROOT.glob("*/*/ssz_static/*/*/*/serialized.ssz_snappy"),
    }
)


def _id(path):
    return "/".join(path.parts[-7:-1])


@pytest.mark.spec
@pytest.mark.parametrize("path", CASES, ids=_id)
def test_official_ssz_static(path):
    preset, fork, _, name, _, _, _ = path.parts[-7:]
    if fork not in FORKS:
        pytest.skip("Fork outside the requested range")
    codec = get_type(name, fork=fork, preset=preset)
    serialized = snappy.decompress(path.read_bytes())
    roots = yaml.load((path.parent / "roots.yaml").read_text(), Loader=yaml.CSafeLoader)
    expected_root = bytes.fromhex(roots["root"][2:])
    expected_value = yaml.load((path.parent / "value.yaml").read_text(), Loader=yaml.CSafeLoader)
    assert codec.hash_tree_root_from_ssz(serialized) == expected_root
    value = codec.deserialize(serialized)
    assert codec.serialize(value) == serialized
    assert codec.hash_tree_root(value) == expected_root
    assert codec.from_json(expected_value) == value
    assert codec.from_json(codec.to_json(value)) == value
    native = codec.load_ssz(serialized)
    assert native.to_ssz() is serialized
    assert native.hash_tree_root() == expected_root
    assert native.to_obj() == value
    assert json.loads(native.to_json()) == codec.to_json(value)
    native = codec.load_json(json.dumps(expected_value))
    assert native.to_ssz() == serialized
    assert native.hash_tree_root() == expected_root
