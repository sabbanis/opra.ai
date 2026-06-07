"""Policy and approval requirement evaluation for opra.ai."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional

from company_os_core.models import PermissionAction, PolicyDecision, PolicyResult, User
from company_os_core.rbac import RBACEngine
from company_os_core.serialization import to_plain_data


class ApprovalMode(str, Enum):
    """Approval behavior for a policy rule."""

    REQUIRE_ANY = "require_any"
    REQUIRE_ALL = "require_all"


@dataclass(frozen=True)
class ApprovalRule:
    """Rule that requires approval for matching object changes."""

    id: str
    object_type: str
    action: PermissionAction
    required_approvers: tuple[str, ...]
    fields: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""
    mode: ApprovalMode = ApprovalMode.REQUIRE_ALL


@dataclass(frozen=True)
class PolicyEngine:
    """Evaluate RBAC and approval requirements together."""

    rbac: RBACEngine
    approval_rules: tuple[ApprovalRule, ...] = field(default_factory=tuple)

    def evaluate(
        self,
        user: User,
        action: PermissionAction,
        obj: Any,
        fields: tuple[str, ...] = (),
    ) -> PolicyResult:
        rbac_result = self.rbac.authorize(user=user, action=action, obj=obj, fields=fields)
        if rbac_result.decision != PolicyDecision.ALLOW:
            return rbac_result

        data = to_plain_data(obj)
        if not isinstance(data, Mapping):
            return PolicyResult(decision=PolicyDecision.DENY, reasons=("Target object must be mapping-like.",))

        approval_rule = self._matching_approval_rule(action, data, fields)
        if approval_rule is None:
            return rbac_result

        return PolicyResult(
            decision=PolicyDecision.REQUIRES_APPROVAL,
            reasons=(
                approval_rule.reason
                or f"Approval rule {approval_rule.id} requires approval for this change.",
            ),
            required_approvers=approval_rule.required_approvers,
            matched_permissions=rbac_result.matched_permissions,
        )

    def _matching_approval_rule(
        self,
        action: PermissionAction,
        data: Mapping[str, Any],
        fields: tuple[str, ...],
    ) -> Optional[ApprovalRule]:
        object_type = str(data.get("object_type", ""))
        for rule in self.approval_rules:
            if rule.action not in (PermissionAction.ALL, action):
                continue
            if rule.object_type not in ("*", object_type):
                continue
            if rule.fields and not any(field in rule.fields for field in fields):
                continue
            return rule
        return None


def approval_required(
    object_type: str,
    action: PermissionAction,
    required_approvers: tuple[str, ...],
    fields: tuple[str, ...] = (),
    reason: str = "",
    rule_id: str = "approval_required",
) -> ApprovalRule:
    """Convenience constructor for approval rules."""

    return ApprovalRule(
        id=rule_id,
        object_type=object_type,
        action=action,
        fields=fields,
        required_approvers=required_approvers,
        reason=reason,
    )
