"""Extract official SSZ static vectors, without trusting archive paths.

This tool never extracts links or unrelated archive members. Normal test runs
use tools.fetch_vectors to download the newest published release automatically.
"""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

FORKS = {"electra", "fulu", "gloas"}
VECTOR_PATH_PARTS = 8
FILES = {"value.yaml", "roots.yaml", "serialized.ssz_snappy", "manifest.yaml"}


def extract(archive: Path, destination: Path, cases_per_suite: int = 0) -> None:
    count = 0
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            parts = Path(member.name).parts
            if (
                not member.isfile()
                or len(parts) != VECTOR_PATH_PARTS
                or parts[0] != "tests"
                or parts[1] not in {"mainnet", "minimal"}
                or parts[2] not in FORKS
                or parts[3] != "ssz_static"
                or parts[-1] not in FILES
                or any(part in {"..", ".", "/"} for part in parts)
            ):
                continue
            if cases_per_suite and int(parts[6].removeprefix("case_")) >= cases_per_suite:
                continue
            if member.size > 512 * 1024 * 1024:
                raise ValueError(f"Unexpected vector size: {member.name}")
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = stream.extractfile(member)
            with source, target.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            count += 1
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    manifest = {
        "archive": archive.name,
        "sha256": digest.hexdigest(),
        "cases_per_suite": cases_per_suite,
        "files": count,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / f"{archive.stem}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--cases-per-suite", type=int, default=0, help="0 means all cases")
    args = parser.parse_args()
    if args.cases_per_suite < 0:
        parser.error("--cases-per-suite must be nonnegative")
    extract(args.archive, args.destination, args.cases_per_suite)
