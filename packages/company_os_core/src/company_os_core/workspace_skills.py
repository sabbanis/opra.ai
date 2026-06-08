"""Workspace Skill descriptors for governed record operations."""

from __future__ import annotations

from company_os_core.models import PermissionAction
from company_os_core.skills import SkillDescriptor, SkillExecutionMode, SkillPermission


WORKSPACE_CRUD_SKILL_DESCRIPTORS = (
    SkillDescriptor(
        name="record-create",
        description="Create a governed source record in the local workspace.",
        inputs=("object", "request_id"),
        execution_mode=SkillExecutionMode.MUTATE,
        required_permissions=(
            SkillPermission(action=PermissionAction.CREATE, object_type="*"),
        ),
    ),
    SkillDescriptor(
        name="record-read",
        description="Read source records and module summaries from the local workspace.",
        inputs=("path", "module", "object_type"),
        execution_mode=SkillExecutionMode.READ_ONLY,
        required_permissions=(
            SkillPermission(action=PermissionAction.READ, object_type="*"),
        ),
    ),
    SkillDescriptor(
        name="record-update",
        description="Update a governed source record in the local workspace.",
        inputs=("object", "request_id", "fields"),
        execution_mode=SkillExecutionMode.MUTATE,
        required_permissions=(
            SkillPermission(action=PermissionAction.UPDATE, object_type="*"),
        ),
    ),
    SkillDescriptor(
        name="record-delete",
        description="Delete a governed source record from the local workspace with audit evidence.",
        inputs=("path", "object", "request_id"),
        execution_mode=SkillExecutionMode.MUTATE,
        required_permissions=(
            SkillPermission(action=PermissionAction.DELETE, object_type="*"),
        ),
    ),
    SkillDescriptor(
        name="record-propose",
        description="Create a reviewable mutation proposal for a source record.",
        inputs=("object", "request_id", "fields"),
        execution_mode=SkillExecutionMode.PROPOSE_MUTATION,
        required_permissions=(
            SkillPermission(action=PermissionAction.UPDATE, object_type="*"),
        ),
    ),
)


def workspace_crud_skill_descriptors() -> tuple[SkillDescriptor, ...]:
    """Return workspace CRUD Skill descriptors."""

    return WORKSPACE_CRUD_SKILL_DESCRIPTORS
