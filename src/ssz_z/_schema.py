"""Recursive metadata reflected from native SSZ types."""

from typing import Literal, Required, TypedDict


class Schema(TypedDict, total=False):
    """SSZ schema; the available attributes depend on ``kind``."""

    kind: Required[
        Literal[
            "uint",
            "bool",
            "bytevector",
            "bytelist",
            "bitvector",
            "bitlist",
            "vector",
            "list",
            "container",
        ]
    ]
    bits: int
    length: int
    limit: int
    progressive: bool
    element: "Schema"
    fields: dict[str, "Schema"]
