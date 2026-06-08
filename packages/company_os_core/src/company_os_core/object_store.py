"""Local filesystem object store for opra.ai source-of-truth files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from company_os_core.models import BaseObject
from company_os_core.schema import ObjectSchema, ValidationIssue, ValidationResult, validate_object
from company_os_core.serialization import read_yaml, stable_hash, to_plain_data, write_yaml


@dataclass(frozen=True)
class StoredObject:
    """Object data read from local storage."""

    path: Path
    data: Mapping[str, Any]
    content_hash: str


class LocalObjectStore:
    """Read and write source-of-truth objects on the local filesystem."""

    def __init__(self, repo_root: Path, path_map: Optional[Mapping[str, str]] = None) -> None:
        self._repo_root = repo_root
        self._path_map = dict(path_map or {})

    def object_path(self, object_type: str, object_id: str) -> Path:
        if not object_type or not object_type.strip():
            raise ValueError("object_type must be a non-empty string")
        if not object_id or not object_id.strip():
            raise ValueError("object_id must be a non-empty string")

        object_dir = self._path_map.get(object_type, f"objects/{object_type}")
        return self._repo_root / object_dir / f"{object_id}.yaml"

    def write_object(
        self,
        value: BaseObject,
        schema: Optional[ObjectSchema] = None,
    ) -> StoredObject:
        data = to_plain_data(value)
        if schema is not None:
            result = validate_object(data, schema)
            if not result.valid:
                raise ObjectValidationError(result)

        path = self.object_path(value.object_type, value.id)
        write_yaml(path, value)
        return StoredObject(path=path, data=data, content_hash=stable_hash(data))

    def read_object(self, object_type: str, object_id: str) -> StoredObject:
        path = self.object_path(object_type, object_id)
        data = read_yaml(path)
        if not isinstance(data, Mapping):
            raise ValueError(f"Stored object at {path} is not a mapping")
        return StoredObject(path=path, data=data, content_hash=stable_hash(data))

    def delete_object(self, object_type: str, object_id: str) -> StoredObject:
        """Delete a stored source object and return the removed state."""

        stored = self.read_object(object_type=object_type, object_id=object_id)
        stored.path.unlink()
        return stored

    def validate_object_file(self, path: Path, schema: ObjectSchema) -> ValidationResult:
        data = read_yaml(path)
        if not isinstance(data, Mapping):
            return ValidationResult.failed(
                [ValidationIssue(field="<root>", message="stored file must contain an object")]
            )
        return validate_object(data, schema)

    def list_object_ids(self, object_type: str) -> tuple[str, ...]:
        object_dir = self.object_path(object_type, "__placeholder__").parent
        if not object_dir.exists():
            return ()
        return tuple(sorted(path.stem for path in object_dir.glob("*.yaml")))


class ObjectValidationError(ValueError):
    """Raised when an object fails schema validation before storage."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        messages = "; ".join(f"{issue.field}: {issue.message}" for issue in result.issues)
        super().__init__(messages or "object validation failed")
