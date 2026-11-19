"""Guard schema generation against incomplete specification checkouts."""

import pytest

from tools.generate_schemas import generate, verify_spec_revision


def test_missing_specifications_preserve_existing_schemas(tmp_path):
    destination = tmp_path / "consensus.zig"
    destination.write_text("existing schemas\n")
    with pytest.raises(ValueError, match="No specification Markdown found for phase0"):
        generate(tmp_path, destination)
    assert destination.read_text() == "existing schemas\n"


def test_specification_provenance(tmp_path):
    import subprocess

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init")
    specs = tmp_path / "specs"
    specs.mkdir()
    source = specs / "example.md"
    source.write_text("original spec")
    git("add", "specs")
    git("-c", "commit.gpgsign=false", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "spec")
    commit = git("rev-parse", "HEAD")
    verify_spec_revision(tmp_path, commit)
    with pytest.raises(ValueError, match="Expected clean"):
        verify_spec_revision(tmp_path, "0" * 40)
    source.write_text("edited spec")
    with pytest.raises(ValueError, match="Expected clean"):
        verify_spec_revision(tmp_path, commit)
