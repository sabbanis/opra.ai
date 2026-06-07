"""RBAC evaluation for opra.ai."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from company_os_core.models import (
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyResult,
    Role,
    User,
)
from company_os_core.serialization import to_plain_data


class RBACEngine:
    """Evaluate role, team, and user permissions against objects."""

    def __init__(self, roles: tuple[Role, ...], direct_permissions: tuple[Permission, ...] = ()) -> None:
        self._roles = {role.id: role for role in roles}
        self._direct_permissions = direct_permissions

    def authorize(
        self,
        user: User,
        action: PermissionAction,
        obj: Any,
        fields: tuple[str, ...] = (),
    ) -> PolicyResult:
        data = to_plain_data(obj)
        if not isinstance(data, Mapping):
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reasons=("Target object must be mapping-like.",),
            )

        matched_permissions = []
        deny_reasons = []
        for permission in self._permissions_for(user):
            if not self._permission_action_matches(permission, action):
                continue
            if not self._permission_object_matches(permission, data):
                continue
            if not self._permission_subject_matches(permission, user):
                continue
            if not self._permission_scope_matches(permission, user, data):
                deny_reasons.append(f"{permission.subject}:{permission.action.value}:{permission.object_type} scope mismatch")
                continue
            if not self._permission_fields_match(permission, fields):
                denied = ", ".join(field for field in fields if field not in permission.fields)
                deny_reasons.append(f"Fields not permitted: {denied}")
                continue

            matched_permissions.append(
                f"{permission.subject}:{permission.action.value}:{permission.object_type}:{permission.scope}"
            )

        if matched_permissions:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reasons=("Permission matched.",),
                matched_permissions=tuple(matched_permissions),
            )

        return PolicyResult(
            decision=PolicyDecision.DENY,
            reasons=tuple(deny_reasons) or ("No matching permission.",),
        )

    def _permissions_for(self, user: User) -> tuple[Permission, ...]:
        permissions = list(self._direct_permissions)
        for role_id in user.roles:
            role = self._roles.get(role_id)
            if role is not None:
                permissions.extend(role.permissions)
        return tuple(permissions)

    def _permission_action_matches(self, permission: Permission, action: PermissionAction) -> bool:
        return permission.action in (PermissionAction.ALL, action)

    def _permission_object_matches(self, permission: Permission, data: Mapping[str, Any]) -> bool:
        object_type = str(data.get("object_type", ""))
        return permission.object_type in ("*", object_type)

    def _permission_subject_matches(self, permission: Permission, user: User) -> bool:
        subject = permission.subject
        return subject in _user_subjects(user)

    def _permission_scope_matches(
        self,
        permission: Permission,
        user: User,
        data: Mapping[str, Any],
    ) -> bool:
        scope = permission.scope
        if scope in ("*", "company", "all"):
            return True
        if scope in ("owned_by_me", "assigned_to_me", "own"):
            return str(data.get("owner", "")) in (user.id, user.username)
        if scope == "self":
            return str(data.get("id", "")) in (user.id, user.username)
        if scope == "team":
            return _object_team(data) in user.teams
        return False

    def _permission_fields_match(self, permission: Permission, fields: tuple[str, ...]) -> bool:
        if not fields:
            return True
        if not permission.fields:
            return True
        return all(field in permission.fields for field in fields)


def _user_subjects(user: User) -> tuple[str, ...]:
    subjects = [user.id, user.username]
    subjects.extend(user.roles)
    subjects.extend(f"role:{role_id}" for role_id in user.roles)
    subjects.extend(user.teams)
    subjects.extend(f"team:{team_id}" for team_id in user.teams)
    return tuple(subjects)


def _object_team(data: Mapping[str, Any]) -> Optional[str]:
    metadata = data.get("metadata")
    if isinstance(metadata, Mapping):
        team = metadata.get("team")
        if isinstance(team, str):
            return team
    return None
