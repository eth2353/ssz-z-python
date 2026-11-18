import hashlib
import io
import tarfile

import pytest

from tools.fetch_native import fetch


def dependency(tmp_path, member="upstream/src/root.zig"):
    archive = tmp_path / "upstream.tar.gz"
    content = b"pub const answer = 42;\n"
    with tarfile.open(archive, "w:gz") as output:
        info = tarfile.TarInfo(member)
        info.size = len(content)
        output.addfile(info, io.BytesIO(content))
    return {
        "commit": "test-commit",
        "archive_url": archive.as_uri(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }


def test_fetch_and_reuse_without_network(tmp_path, monkeypatch):
    entry = dependency(tmp_path)
    cache = tmp_path / "cache"
    source = fetch("test", entry, cache)
    assert (source / "src/root.zig").read_bytes() == b"pub const answer = 42;\n"

    def unexpected_download(*args, **kwargs):
        pytest.fail("Cached native sources must not require a network connection")

    monkeypatch.setattr("urllib.request.urlopen", unexpected_download)
    assert fetch("test", entry, cache) == source


def test_checksum_mismatch_does_not_populate_cache(tmp_path):
    entry = dependency(tmp_path)
    entry["archive_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch("test", entry, tmp_path / "cache")
    assert not (tmp_path / "cache/test/test-commit").exists()


def test_archive_cannot_escape_extraction_directory(tmp_path):
    entry = dependency(tmp_path, "upstream/src/../../../escaped.zig")
    with pytest.raises(tarfile.OutsideDestinationError):
        fetch("test", entry, tmp_path / "cache")
    assert not (tmp_path / "cache/test/test-commit").exists()
    assert not list(tmp_path.rglob("escaped.zig"))
