"""All official static vectors from the newest published release."""

import json
import os
from pathlib import Path

import pytest
import snappy
import yaml

from ssz_z import get_type
from tests.json_helpers import json_document, json_value
from tools.fetch_vectors import fetch_vectors, vector_cases

YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
ROOT = Path(os.environ["SSZ_SPEC_TESTS"]) if "SSZ_SPEC_TESTS" in os.environ else fetch_vectors()
CASES = vector_cases(ROOT)


def _id(path):
    return "/".join(path.parts[-7:-1])


@pytest.mark.spec
@pytest.mark.parametrize("path", CASES, ids=_id)
def test_official_ssz_static(path):
    (preset, fork, _, name, _, _, _) = path.parts[-7:]
    codec = get_type(name, fork=fork, preset=preset)
    serialized = snappy.decompress(path.read_bytes())
    roots = yaml.load((path.parent / "roots.yaml").read_text(), Loader=YAML_LOADER)  # noqa: S506 - YAML_LOADER is CSafeLoader or SafeLoader.
    expected_root = bytes.fromhex(roots["root"][2:])
    expected_value = yaml.load((path.parent / "value.yaml").read_text(), Loader=YAML_LOADER)  # noqa: S506 - YAML_LOADER is CSafeLoader or SafeLoader.
    assert codec.hash_tree_root_from_ssz(serialized) == expected_root
    value = codec.load_ssz(serialized)
    assert value.to_ssz() is serialized
    assert value.hash_tree_root() == expected_root
    # Compare independently published YAML values with native JSON output.
    document = value.to_json()
    assert json.loads(document) == json_value(expected_value)
    for source in (document, json_document(expected_value)):
        restored = codec.load_json(source)
        assert restored.to_ssz() == serialized
        assert restored.hash_tree_root() == expected_root
