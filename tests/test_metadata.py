"""Verify that installed provenance and native ABI match the build manifest."""

import json
import re
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from ssz_z import FORKS, PRESETS, SPEC_VERSION, UPSTREAM_COMMIT, __version__
from ssz_z._metadata import ABI_VERSION
from ssz_z._native import Operation, _library

ROOT = Path(__file__).resolve().parents[1]


def test_installed_manifest_and_libraries():
    manifest = json.loads((ROOT / "UPSTREAM.json").read_text())
    assert json.loads(files("ssz_z").joinpath("_upstream.json").read_text()) == manifest
    assert tuple(manifest["bindings"]["presets"]) == PRESETS
    assert tuple(manifest["bindings"]["forks"]) == FORKS
    assert manifest["lodestar"]["commit"] == UPSTREAM_COMMIT
    assert manifest["consensus-specs"]["tag"] == SPEC_VERSION
    assert __version__ == version("ssz-z-python")
    assert all(_library(preset).ssz_z_abi_version() == ABI_VERSION for preset in PRESETS)


def test_native_operation_numbers_match_python():
    source = (ROOT / "native" / "bindings.zig").read_text()
    operations = re.findall(r"^    ([a-z_]+) = (\d+),$", source, re.MULTILINE)
    assert {name.upper(): int(number) for name, number in operations} == {
        operation.name: operation.value for operation in Operation
    }
