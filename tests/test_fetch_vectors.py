import hashlib
import io
import json
import tarfile
from unittest.mock import Mock

import pytest

from tools import fetch_vectors as vectors


@pytest.fixture
def release(tmp_path, monkeypatch):
    assets = []
    for index, preset in enumerate(vectors.PRESETS):
        archive = tmp_path / f"{preset}.tar.gz"
        with tarfile.open(archive, "w:gz") as output:
            for fork in vectors.FORKS:
                for name in ("serialized.ssz_snappy", "roots.yaml", "value.yaml"):
                    member = tarfile.TarInfo(
                        f"tests/{preset}/{fork}/ssz_static/Test/ssz_random/case_0/{name}"
                    )
                    member.size = 1
                    output.addfile(member, io.BytesIO(b"x"))
        assets.append(
            {
                "id": index,
                "name": archive.name,
                "browser_download_url": archive.as_uri(),
                "digest": "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
        )
    release = {"id": 1, "tag_name": "v-next", "assets": assets}
    monkeypatch.setattr(vectors, "latest_release", lambda: release)
    return release


def test_download_cache_and_asset_replacement(tmp_path, monkeypatch, release):
    lookup = Mock(return_value=release)
    monkeypatch.setattr(vectors, "latest_release", lookup)
    cache = tmp_path / "cache"
    root = vectors.fetch_vectors(cache)
    assert len(vectors.vector_cases(root)) == 6
    assert json.loads((root.parent / "release.json").read_text())["release"] == "v-next"
    # Cached assets do not need downloading, but each call still resolves the release.
    with monkeypatch.context() as context:
        context.setattr(
            vectors.urllib.request, "urlopen", lambda *a, **kw: pytest.fail("Unexpected download")
        )
        assert vectors.fetch_vectors(cache) == root
    release["assets"][0]["id"] = 99
    assert vectors.fetch_vectors(cache) != root
    assert lookup.call_count == 3


def test_checksum_failure_never_publishes_cache(tmp_path, release):
    release["assets"][0]["digest"] = "sha256:" + "0" * 64
    cache = tmp_path / "cache"
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        vectors.fetch_vectors(cache)
    assert not list(cache.iterdir())


def test_empty_or_incomplete_vectors_fail(tmp_path, release):
    with pytest.raises(ValueError, match="Missing official SSZ vectors"):
        vectors.vector_cases(tmp_path)
    root = vectors.fetch_vectors(tmp_path / "cache")
    vectors.vector_cases(root)[0].with_name("roots.yaml").unlink()
    with pytest.raises(ValueError, match="Incomplete official SSZ vector"):
        vectors.fetch_vectors(tmp_path / "cache")


def test_latest_includes_prereleases_and_excludes_drafts(monkeypatch):
    releases = [
        {"tag_name": "stable", "published_at": "2026-01-01", "draft": False},
        {"tag_name": "beta", "published_at": "2026-02-01", "draft": False, "prerelease": True},
        {"tag_name": "draft", "published_at": "2026-03-01", "draft": True},
    ]
    monkeypatch.setattr(
        vectors.urllib.request,
        "urlopen",
        lambda *a, **kw: io.BytesIO(json.dumps(releases).encode()),
    )
    assert vectors.latest_release()["tag_name"] == "beta"
