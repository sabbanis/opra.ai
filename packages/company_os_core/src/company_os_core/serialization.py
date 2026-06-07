"""Deterministic serialization helpers for opra.ai objects."""

from __future__ import annotations

import json
import re
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Optional, Union


_SAFE_UNQUOTED = re.compile(r"^[A-Za-z0-9_./@+:-]+$")
_YAML_KEYWORDS = {"null", "true", "false", "yes", "no", "on", "off"}


def to_plain_data(value: Any) -> Any:
    """Convert dataclasses, enums, datetimes, and tuples into plain data."""

    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: to_plain_data(getattr(value, item.name))
            for item in fields(value)
            if getattr(value, item.name) is not None
        }

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return _format_datetime(value)

    if isinstance(value, Mapping):
        return {str(key): to_plain_data(item) for key, item in value.items()}

    if isinstance(value, (tuple, list)):
        return [to_plain_data(item) for item in value]

    return value


def to_json(value: Any) -> str:
    """Serialize a opra.ai value to deterministic JSON."""

    return json.dumps(to_plain_data(value), indent=2, sort_keys=False)


def stable_hash(value: Any) -> str:
    """Return a stable SHA-256 hash for a opra.ai value."""

    payload = json.dumps(to_plain_data(value), separators=(",", ":"), sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def to_yaml(value: Any) -> str:
    """Serialize a opra.ai value to deterministic, human-readable YAML."""

    return _dump_yaml(to_plain_data(value), indent=0) + "\n"


def write_yaml(path: Path, value: Any) -> None:
    """Write a opra.ai value as YAML."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_yaml(value), encoding="utf-8")


def read_yaml(path: Path) -> Any:
    """Read YAML emitted by `to_yaml`.

    This parser is intentionally small and supports the deterministic subset emitted by this
    package: mappings, lists, strings, numbers, booleans, nulls, and empty objects/lists.
    """

    return from_yaml(path.read_text(encoding="utf-8"))


def from_yaml(document: str) -> Any:
    """Parse YAML emitted by `to_yaml` into plain Python data."""

    lines = _prepare_lines(document)
    if not lines:
        return {}

    value, next_index = _parse_block(lines, 0, lines[0][0])
    if next_index != len(lines):
        raise ValueError(f"Unexpected YAML content on line {next_index + 1}")
    return value


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime values must include timezone information")
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def _dump_yaml(value: Any, indent: int) -> str:
    if isinstance(value, Mapping):
        return _dump_mapping(value, indent)

    if isinstance(value, list):
        return _dump_list(value, indent)

    return _format_scalar(value)


def _dump_mapping(value: Mapping[str, Any], indent: int) -> str:
    if not value:
        return "{}"

    lines = []
    prefix = " " * indent
    for key, item in value.items():
        if _is_inline(item):
            lines.append(f"{prefix}{key}: {_format_inline(item)}")
        else:
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_yaml(item, indent + 2))
    return "\n".join(lines)


def _dump_list(value: list[Any], indent: int) -> str:
    if not value:
        return "[]"

    lines = []
    prefix = " " * indent
    for item in value:
        if _is_inline(item):
            lines.append(f"{prefix}- {_format_inline(item)}")
        elif isinstance(item, Mapping):
            nested = _dump_mapping(item, indent + 2).splitlines()
            if not nested:
                lines.append(f"{prefix}- {{}}")
            else:
                first = nested[0].lstrip()
                lines.append(f"{prefix}- {first}")
                lines.extend(nested[1:])
        else:
            lines.append(f"{prefix}-")
            lines.append(_dump_yaml(item, indent + 2))
    return "\n".join(lines)


def _is_inline(value: Any) -> bool:
    return not isinstance(value, (Mapping, list)) or value == {} or value == []


def _format_inline(value: Any) -> str:
    if isinstance(value, Mapping):
        return "{}"
    if isinstance(value, list):
        return "[]"
    return _format_scalar(value)


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _format_string(value)
    raise TypeError(f"Unsupported YAML scalar type: {type(value).__name__}")


def _format_string(value: str) -> str:
    if not value:
        return '""'
    if value.lower() in _YAML_KEYWORDS:
        return json.dumps(value)
    if _SAFE_UNQUOTED.match(value):
        return value
    return json.dumps(value)


def _prepare_lines(document: str) -> list[tuple[int, str]]:
    prepared = []
    for raw_line in document.splitlines():
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError("YAML indentation must use multiples of two spaces")
        prepared.append((indent, raw_line.strip()))
    return prepared


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index

    current_indent, content = lines[index]
    if current_indent != indent:
        raise ValueError(f"Expected indentation {indent} on line {index + 1}")

    if content.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
    stop_at_list_item: bool = False,
) -> tuple[dict[str, Any], int]:
    values: dict[str, Any] = {}

    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"Unexpected indentation on line {index + 1}")
        if content.startswith("- "):
            if stop_at_list_item:
                break
            raise ValueError(f"Unexpected list item on line {index + 1}")

        key, item = _split_key_value(content, index)
        if item:
            values[key] = _parse_scalar(item)
            index += 1
            continue

        next_index = index + 1
        if next_index >= len(lines) or lines[next_index][0] <= indent:
            values[key] = {}
            index = next_index
            continue

        values[key], index = _parse_block(lines, next_index, indent + 2)

    return values, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    values = []

    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"Unexpected indentation on line {index + 1}")
        if not content.startswith("- "):
            break

        item = content[2:]
        if not item:
            nested_value, index = _parse_nested_list_value(lines, index, indent)
            values.append(nested_value)
            continue

        if _looks_like_mapping_item(item):
            parsed_item, index = _parse_list_mapping_item(lines, index, indent, item)
            values.append(parsed_item)
            continue

        values.append(_parse_scalar(item))
        index += 1

    return values, index


def _parse_nested_list_value(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    next_index = index + 1
    if next_index >= len(lines) or lines[next_index][0] <= indent:
        return None, next_index
    return _parse_block(lines, next_index, indent + 2)


def _parse_list_mapping_item(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
    item: str,
) -> tuple[dict[str, Any], int]:
    key, value = _split_key_value(item, index)
    parsed_item = {key: _parse_scalar(value) if value else {}}
    index += 1

    if index < len(lines) and lines[index][0] == indent + 2:
        continuation, index = _parse_mapping(lines, index, indent + 2, stop_at_list_item=True)
        parsed_item.update(continuation)

    return parsed_item, index


def _looks_like_mapping_item(item: str) -> bool:
    if ": " in item:
        return True
    return item.endswith(":")


def _split_key_value(content: str, line_index: int) -> tuple[str, str]:
    if ":" not in content:
        raise ValueError(f"Expected mapping entry on line {line_index + 1}")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Expected mapping key on line {line_index + 1}")
    return key, value.strip()


def _parse_scalar(value: str) -> Any:
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith('"'):
        parsed = json.loads(value)
        if not isinstance(parsed, str):
            raise ValueError("Quoted YAML scalar must decode to a string")
        return parsed

    number = _parse_number(value)
    if number is not None:
        return number

    return value


def _parse_number(value: str) -> Optional[Union[int, float]]:
    if re.match(r"^-?[0-9]+$", value):
        return int(value)
    if re.match(r"^-?[0-9]+\.[0-9]+$", value):
        return float(value)
    return None
