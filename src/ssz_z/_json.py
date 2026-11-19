"""JSON decoders for native schema and response metadata."""

import json

from ._native import SSZError


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SSZError(f"Duplicate JSON field {key!r}")
        result[key] = value
    return result


def decode_metadata(data: bytes) -> dict:
    """Decode only the small native metadata envelope, rejecting duplicate keys."""
    try:
        return json.loads(data, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise SSZError(f"Invalid JSON metadata: {error}") from error
