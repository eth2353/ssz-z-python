"""JSON decoders for native schema and response metadata."""

import json
from typing import TypedDict, cast

from ._native import SSZError

type JSONValue = bool | int | float | str | list[JSONValue] | dict[str, JSONValue] | None


class MetadataEnvelope(TypedDict):
    metadata: dict[str, JSONValue]
    data_start: int
    data_end: int


def _unique_object(pairs: list[tuple[str, JSONValue]]) -> dict[str, JSONValue]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SSZError(f"Duplicate JSON field {key!r}")
        result[key] = value
    return result


def decode_metadata(data: bytes) -> MetadataEnvelope:
    """Decode only the small native metadata envelope, rejecting duplicate keys."""
    try:
        # The native REST_METADATA operation owns this envelope schema.
        return cast("MetadataEnvelope", json.loads(data, object_pairs_hook=_unique_object))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise SSZError(f"Invalid JSON metadata: {error}") from error
