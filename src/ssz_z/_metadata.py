"""Installed snapshot of the authoritative build manifest."""

import json
from importlib.resources import files

_UPSTREAM = json.loads(files("ssz_z").joinpath("_upstream.json").read_text())
ABI_VERSION: int = _UPSTREAM["bindings"]["abi_version"]
PRESETS: tuple[str, ...] = tuple(_UPSTREAM["bindings"]["presets"])
FORKS: tuple[str, ...] = tuple(_UPSTREAM["bindings"]["forks"])
UPSTREAM_COMMIT: str = _UPSTREAM["lodestar"]["commit"]
SPEC_VERSION: str = _UPSTREAM["consensus-specs"]["tag"]
