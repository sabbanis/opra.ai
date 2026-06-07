"""Schema validation primitives for opra.ai source-of-truth objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional

from company_os_core.models import ObjectStatus, ObjectVisibility
from company_os_core.serialization import to_plain_data


class FieldType(str, Enum):
    """Field types supported by the dependency-free schema engine."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    TIMESTAMP = "timestamp"
    DATE = "date"


@dataclass(frozen=True)
class FieldSchema:
    """Validation rule for one object field."""

    name: str
    field_type: FieldType
    required: bool = True
    allowed_values: tuple[Any, ...] = field(default_factory=tuple)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    item_type: Optional[FieldType] = None


@dataclass(frozen=True)
class ObjectSchema:
    """Validation rules for a source-of-truth object type."""

    object_type: str
    version: int
    fields: tuple[FieldSchema, ...]
    allow_extra_fields: bool = False


@dataclass(frozen=True)
class ValidationIssue:
    """One schema validation issue."""

    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Schema validation result."""

    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(valid=True)

    @classmethod
    def failed(cls, issues: list[ValidationIssue]) -> "ValidationResult":
        return cls(valid=False, issues=tuple(issues))


class SchemaRegistry:
    """Registry of object schemas by object type."""

    def __init__(self, schemas: tuple[ObjectSchema, ...]) -> None:
        self._schemas = {schema.object_type: schema for schema in schemas}

    def schema_for(self, object_type: str) -> ObjectSchema:
        try:
            return self._schemas[object_type]
        except KeyError as exc:
            raise KeyError(f"No schema registered for object_type {object_type!r}") from exc

    def validate(self, value: Any) -> ValidationResult:
        data = to_plain_data(value)
        if not isinstance(data, Mapping):
            return ValidationResult.failed(
                [ValidationIssue(field="<root>", message="value must be an object")]
            )

        object_type = data.get("object_type")
        if not isinstance(object_type, str) or not object_type:
            return ValidationResult.failed(
                [ValidationIssue(field="object_type", message="object_type is required")]
            )

        try:
            schema = self.schema_for(object_type)
        except KeyError as exc:
            return ValidationResult.failed(
                [ValidationIssue(field="object_type", message=str(exc))]
            )

        return validate_object(data, schema)


def base_object_schema(object_type: str = "base_object") -> ObjectSchema:
    """Return the common opra.ai base object schema."""

    return ObjectSchema(
        object_type=object_type,
        version=1,
        fields=(
            FieldSchema("id", FieldType.STRING),
            FieldSchema("object_type", FieldType.STRING, allowed_values=(object_type,)),
            FieldSchema("owner", FieldType.STRING),
            FieldSchema("created_by", FieldType.STRING),
            FieldSchema("updated_by", FieldType.STRING),
            FieldSchema("created_at", FieldType.TIMESTAMP),
            FieldSchema("updated_at", FieldType.TIMESTAMP),
            FieldSchema("version", FieldType.INTEGER, min_value=1),
            FieldSchema(
                "status",
                FieldType.STRING,
                allowed_values=tuple(status.value for status in ObjectStatus),
            ),
            FieldSchema(
                "visibility",
                FieldType.STRING,
                allowed_values=tuple(visibility.value for visibility in ObjectVisibility),
            ),
            FieldSchema("links", FieldType.ARRAY, item_type=FieldType.OBJECT),
            FieldSchema("tags", FieldType.ARRAY, item_type=FieldType.STRING),
            FieldSchema("metadata", FieldType.OBJECT),
        ),
    )


def validate_object(data: Mapping[str, Any], schema: ObjectSchema) -> ValidationResult:
    """Validate one plain object against an object schema."""

    issues: list[ValidationIssue] = []
    field_rules = {field_rule.name: field_rule for field_rule in schema.fields}

    for field_rule in schema.fields:
        if field_rule.required and field_rule.name not in data:
            issues.append(ValidationIssue(field_rule.name, "field is required"))
            continue
        if field_rule.name not in data:
            continue
        _validate_field(data[field_rule.name], field_rule, issues)

    if not schema.allow_extra_fields:
        for field_name in data:
            if field_name not in field_rules:
                issues.append(ValidationIssue(field_name, "field is not allowed by schema"))

    if issues:
        return ValidationResult.failed(issues)
    return ValidationResult.ok()


def _validate_field(value: Any, field_rule: FieldSchema, issues: list[ValidationIssue]) -> None:
    if not _matches_type(value, field_rule.field_type):
        issues.append(
            ValidationIssue(
                field_rule.name,
                f"expected {field_rule.field_type.value}, got {type(value).__name__}",
            )
        )
        return

    if field_rule.allowed_values and value not in field_rule.allowed_values:
        allowed = ", ".join(str(item) for item in field_rule.allowed_values)
        issues.append(ValidationIssue(field_rule.name, f"must be one of: {allowed}"))

    if field_rule.min_value is not None and value < field_rule.min_value:
        issues.append(
            ValidationIssue(field_rule.name, f"must be greater than or equal to {field_rule.min_value}")
        )

    if field_rule.max_value is not None and value > field_rule.max_value:
        issues.append(
            ValidationIssue(field_rule.name, f"must be less than or equal to {field_rule.max_value}")
        )

    if field_rule.field_type == FieldType.ARRAY and field_rule.item_type is not None:
        for index, item in enumerate(value):
            if not _matches_type(item, field_rule.item_type):
                issues.append(
                    ValidationIssue(
                        f"{field_rule.name}[{index}]",
                        f"expected {field_rule.item_type.value}, got {type(item).__name__}",
                    )
                )


def _matches_type(value: Any, field_type: FieldType) -> bool:
    if field_type == FieldType.STRING:
        return isinstance(value, str) and bool(value.strip())
    if field_type == FieldType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == FieldType.NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if field_type == FieldType.BOOLEAN:
        return isinstance(value, bool)
    if field_type == FieldType.OBJECT:
        return isinstance(value, Mapping)
    if field_type == FieldType.ARRAY:
        return isinstance(value, list)
    if field_type == FieldType.TIMESTAMP:
        return isinstance(value, str) and _is_utc_timestamp(value)
    if field_type == FieldType.DATE:
        return isinstance(value, str) and _is_date(value)
    return False


def _is_utc_timestamp(value: str) -> bool:
    return bool(re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", value))


def _is_date(value: str) -> bool:
    return bool(re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", value))


def extend_schema(
    base_schema: ObjectSchema,
    fields: tuple[FieldSchema, ...],
    allow_extra_fields: Optional[bool] = None,
) -> ObjectSchema:
    """Return a schema with additional fields appended to a base schema."""

    return ObjectSchema(
        object_type=base_schema.object_type,
        version=base_schema.version,
        fields=base_schema.fields + fields,
        allow_extra_fields=(
            base_schema.allow_extra_fields if allow_extra_fields is None else allow_extra_fields
        ),
    )
