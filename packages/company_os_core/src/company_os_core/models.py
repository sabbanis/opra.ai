"""Core domain models for opra.ai."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class ObjectStatus(str, Enum):
    """Common lifecycle status for source-of-truth objects."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ObjectVisibility(str, Enum):
    """Common object visibility levels."""

    PUBLIC = "public"
    COMPANY = "company"
    TEAM = "team"
    PRIVATE = "private"
    HR_PRIVATE = "hr_private"


class AuditAction(str, Enum):
    """Audit event action types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    EXECUTE = "execute"
    IMPORT = "import"


class EventResult(str, Enum):
    """Audit event result values."""

    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    REQUIRES_APPROVAL = "requires_approval"


class SourceInterface(str, Enum):
    """Interfaces that can initiate opra.ai actions."""

    CLI = "cli"
    API = "api"
    WEB = "web"
    SKILL = "skill"
    GITHUB = "github"
    WORKER = "worker"
    IMPORTER = "importer"


class PermissionAction(str, Enum):
    """Actions controlled by RBAC permissions."""

    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    EXECUTE = "execute"
    ADMIN = "admin"
    ALL = "*"


class PolicyDecision(str, Enum):
    """Policy evaluation outcomes."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass(frozen=True)
class ObjectLink:
    """Typed link from one business object to another."""

    target_type: str
    target_id: str
    relationship: str

    def __post_init__(self) -> None:
        _require_non_empty("target_type", self.target_type)
        _require_non_empty("target_id", self.target_id)
        _require_non_empty("relationship", self.relationship)


@dataclass(frozen=True)
class BaseObject:
    """Base source-of-truth business object contract."""

    id: str
    object_type: str
    owner: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
    status: ObjectStatus = ObjectStatus.ACTIVE
    visibility: ObjectVisibility = ObjectVisibility.COMPANY
    links: tuple[ObjectLink, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("object_type", self.object_type)
        _require_non_empty("owner", self.owner)
        _require_non_empty("created_by", self.created_by)
        _require_non_empty("updated_by", self.updated_by)
        if self.version < 1:
            raise ValueError("version must be greater than or equal to 1")
        _require_datetime("created_at", self.created_at)
        _require_datetime("updated_at", self.updated_at)


@dataclass(frozen=True)
class EventSource:
    """Source metadata for an audit event."""

    interface: SourceInterface
    request_id: str

    def __post_init__(self) -> None:
        _require_non_empty("request_id", self.request_id)


@dataclass(frozen=True)
class ApprovalDecision:
    """Approval decision captured in an audit chain."""

    approver: str
    decision: str
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_non_empty("approver", self.approver)
        _require_non_empty("decision", self.decision)
        _require_datetime("timestamp", self.timestamp)


@dataclass(frozen=True)
class AuditEvent:
    """Append-only audit event contract."""

    event_id: str
    timestamp: datetime
    actor: str
    action: AuditAction
    object_type: str
    object_id: str
    before_hash: Optional[str]
    after_hash: Optional[str]
    source: EventSource
    result: EventResult
    approval_chain: tuple[ApprovalDecision, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_non_empty("event_id", self.event_id)
        _require_datetime("timestamp", self.timestamp)
        _require_non_empty("actor", self.actor)
        _require_non_empty("object_type", self.object_type)
        _require_non_empty("object_id", self.object_id)


@dataclass(frozen=True)
class User:
    """opra.ai user identity."""

    id: str
    username: str
    email: str = ""
    display_name: str = ""
    teams: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("username", self.username)


@dataclass(frozen=True)
class Permission:
    """RBAC permission tuple."""

    subject: str
    action: PermissionAction
    object_type: str
    scope: str
    condition: Optional[str] = None
    fields: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_non_empty("subject", self.subject)
        _require_non_empty("object_type", self.object_type)
        _require_non_empty("scope", self.scope)


@dataclass(frozen=True)
class Role:
    """Named collection of permissions."""

    id: str
    name: str
    permissions: tuple[Permission, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("name", self.name)


@dataclass(frozen=True)
class PolicyResult:
    """Result returned by RBAC and policy evaluations."""

    decision: PolicyDecision
    reasons: tuple[str, ...] = field(default_factory=tuple)
    required_approvers: tuple[str, ...] = field(default_factory=tuple)
    matched_permissions: tuple[str, ...] = field(default_factory=tuple)


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _require_non_empty(field_name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_datetime(field_name: str, value: datetime) -> None:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone information")
