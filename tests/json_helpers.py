"""Build JSON test documents; object conversion is deliberately test-side only."""

import json


def json_value(value):
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if type(value) is int:
        return str(value)
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def json_document(value):
    return json.dumps(json_value(value))
