"""Skill contract primitives for opra.ai."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from company_os_core.models import PermissionAction, PolicyDecision


class SkillExecutionMode(str, Enum):
    """Skill execution behavior."""

    READ_ONLY = "read_only"
    PROPOSE_MUTATION = "propose_mutation"
    MUTATE = "mutate"


@dataclass(frozen=True)
class SkillPermission:
    """Permission required by a Skill."""

    action: PermissionAction
    object_type: str


@dataclass(frozen=True)
class SkillDescriptor:
    """Public description of a Skill handler."""

    name: str
    description: str
    inputs: tuple[str, ...]
    execution_mode: SkillExecutionMode
    required_permissions: tuple[SkillPermission, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SkillResult:
    """Result returned by a Skill handler."""

    name: str
    decision: PolicyDecision
    summary: str
    data: Mapping[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW
