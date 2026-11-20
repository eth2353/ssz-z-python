"""Fetch unchanged, checksummed native sources into the ignored build cache."""

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = ("lodestar", "hashtree-z", "hashtree")


def fetch(name, entry, cache_root):
    destination = cache_root / name / entry["commit"]
    marker = destination / ".archive-sha256"
    expected = entry["archive_sha256"]
    if marker.is_file() and marker.read_text() == expected and (destination / "src").is_dir():
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary_name:
        temporary = Path(temporary_name)
        download = temporary / "source.tar.gz"
        with (
            urllib.request.urlopen(entry["archive_url"], timeout=60) as response,  # noqa: S310 - Checksummed archive; tests use file URLs.
            download.open("wb") as output,
        ):
            shutil.copyfileobj(response, output)
        with download.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {name}: expected {expected}, got {actual}")

        extracted = temporary / "extracted"
        with tarfile.open(download) as archive:
            members = [
                member
                for member in archive.getmembers()
                if len(Path(member.name).parts) > 1 and Path(member.name).parts[1] == "src"
            ]
            roots = {Path(member.name).parts[0] for member in members}
            if len(roots) != 1:
                raise ValueError(f"Expected one source directory in {name}")
            archive.extractall(extracted, members=members, filter="data")
        source_root = extracted / roots.pop()
        (source_root / ".archive-sha256").write_text(expected)
        if destination.exists():
            # Another build may have populated the same immutable cache entry.
            if marker.is_file() and marker.read_text() == expected:
                return destination
            raise ValueError(f"Incomplete native cache entry: remove {destination} and retry")
        try:
            source_root.rename(destination)
        except OSError:
            if not marker.is_file() or marker.read_text() != expected:
                raise
        print(f"Fetched {name} at {entry['commit']}", flush=True)
    return destination


def main():
    manifest = json.loads((ROOT / "UPSTREAM.json").read_text())
    for name in DEPENDENCIES:
        fetch(name, manifest[name], ROOT / "build" / "deps")


if __name__ == "__main__":
    main()
