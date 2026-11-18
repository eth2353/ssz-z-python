"""Guard schema generation against incomplete specification checkouts."""

import pytest

from tools.generate_schemas import generate


def test_missing_specifications_preserve_existing_schemas(tmp_path):
    destination = tmp_path / "consensus.zig"
    destination.write_text("existing schemas\n")
    with pytest.raises(ValueError, match="No specification Markdown found for phase0"):
        generate(tmp_path, destination)
    assert destination.read_text() == "existing schemas\n"
