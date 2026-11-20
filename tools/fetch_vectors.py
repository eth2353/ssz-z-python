"""Cache the newest published consensus-specs vectors, including prereleases."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

from tools.extract_vectors import FORKS, extract

ROOT = Path(__file__).resolve().parents[1]
RELEASES = "https://api.github.com/repos/ethereum/consensus-specs/releases?per_page=100"
PRESETS = ("mainnet", "minimal")


def latest_release():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ssz-z-python-tests"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(RELEASES, headers=headers), timeout=60) as r:
        releases = json.load(r)
    return max(
        (release for release in releases if not release["draft"] and release["published_at"]),
        key=lambda release: release["published_at"],
    )


def vector_cases(root):
    """Require complete static suites for every supported fork and Ethereum preset."""
    cases = []
    for preset in PRESETS:
        for fork in sorted(FORKS):
            suite = root / preset / fork / "ssz_static"
            found = sorted(suite.glob("*/*/*/serialized.ssz_snappy"))
            if not found:
                raise ValueError(f"Missing official SSZ vectors: {suite}")
            for case in found:
                for name in ("value.yaml", "roots.yaml"):
                    if not case.with_name(name).is_file():
                        raise ValueError(f"Incomplete official SSZ vector: {case.parent}")
            cases.extend(found)
    return cases


def cache_key(release):
    assets = {asset["name"]: asset for asset in release["assets"]}
    return "-".join(str(assets[f"{preset}.tar.gz"]["id"]) for preset in PRESETS)


def fetch_vectors(cache_root=ROOT / "fixtures" / "releases"):
    release = latest_release()
    assets = {asset["name"]: asset for asset in release["assets"]}
    selected = [assets[f"{preset}.tar.gz"] for preset in PRESETS]
    provenance = {
        "release": release["tag_name"],
        "release_id": release["id"],
        "assets": [{key: asset[key] for key in ("id", "name", "digest")} for asset in selected],
    }
    # Asset IDs also change when a release replaces its archives.
    key = cache_key(release)
    destination = cache_root / key
    marker = destination / "release.json"
    if marker.is_file() and json.loads(marker.read_text()) == provenance:
        vector_cases(destination / "tests")
        return destination / "tests"

    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_root) as temporary_name:
        temporary = Path(temporary_name)
        extracted = temporary / "extracted"
        for asset in selected:
            digest = asset["digest"]
            if not digest or not digest.startswith("sha256:"):
                raise ValueError(f"Missing SHA-256 digest for {asset['name']}")
            archive = temporary / asset["name"]
            print(f"Fetching {release['tag_name']} {asset['name']}", flush=True)
            with (
                urllib.request.urlopen(asset["browser_download_url"], timeout=60) as source,  # noqa: S310 - Checksummed archive; tests use file URLs.
                archive.open("wb") as output,
            ):
                shutil.copyfileobj(source, output)
            with archive.open("rb") as source:
                actual = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != f"sha256:{actual}":
                raise ValueError(f"SHA-256 mismatch for {asset['name']}")
            extract(archive, extracted)
            archive.unlink()
        vector_cases(extracted / "tests")
        (extracted / "release.json").write_text(json.dumps(provenance, indent=2) + "\n")
        try:
            extracted.rename(destination)
        except OSError:
            # A concurrent test process may have completed the same release.
            if not marker.is_file() or json.loads(marker.read_text()) != provenance:
                raise
            vector_cases(destination / "tests")
    return destination / "tests"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-key", action="store_true")
    args = parser.parse_args()
    print(cache_key(latest_release()) if args.cache_key else fetch_vectors())
