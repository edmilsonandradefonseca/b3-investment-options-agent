"""Lossless representation of repeated structured facts at the senior boundary."""
from __future__ import annotations
import json
from typing import Any


def serialize_senior_context(payload: dict[str, Any]) -> str:
    # Normalize exactly as the existing JSON boundary before comparing values.
    normalized = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    seen: dict[str, str] = {}

    def visit(value, pointer):
        if isinstance(value, (dict, list)):
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            if len(encoded) >= 512:
                previous = seen.get(encoded)
                if previous is not None:
                    return {'$b3_context_ref': previous}
                seen[encoded] = pointer
            if isinstance(value, dict):
                return {key: visit(item, pointer+'/'+key.replace('~','~0').replace('/','~1')) for key,item in value.items()}
            return [visit(item, pointer+'/'+str(index)) for index,item in enumerate(value)]
        return value

    # Avoid collisions with user/source data that already contains our reserved key.
    def reserved(value):
        if isinstance(value, dict):
            return '$b3_context_ref' in value or any(reserved(item) for item in value.values())
        return isinstance(value, list) and any(reserved(item) for item in value)

    projected = normalized if reserved(normalized) else visit(normalized, '')
    return json.dumps(projected, ensure_ascii=False, separators=(',', ':'))
