"""CRM Skill handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from company_os_core.crm_read_model import (
    CRMAccountReadRow,
    CRMOpportunityReadRow,
    build_crm_read_model,
)
from company_os_core.models import PermissionAction, PolicyDecision, User
from company_os_core.policy import PolicyEngine
from company_os_core.serialization import to_plain_data
from company_os_core.skills import (
    SkillDescriptor,
    SkillExecutionMode,
    SkillPermission,
    SkillResult,
)


CRM_SKILL_DESCRIPTORS = (
    SkillDescriptor(
        name="pipeline-summary",
        description="Summarize ARR, open pipeline, weighted pipeline, and top open opportunities.",
        inputs=("limit",),
        execution_mode=SkillExecutionMode.READ_ONLY,
        required_permissions=(
            SkillPermission(action=PermissionAction.READ, object_type="account"),
            SkillPermission(action=PermissionAction.READ, object_type="opportunity"),
        ),
    ),
    SkillDescriptor(
        name="renewal-health",
        description="List renewal and at-risk accounts that need attention.",
        inputs=("limit",),
        execution_mode=SkillExecutionMode.READ_ONLY,
        required_permissions=(
            SkillPermission(action=PermissionAction.READ, object_type="account"),
        ),
    ),
    SkillDescriptor(
        name="opportunity-view",
        description="List open opportunities, optionally filtered by account.",
        inputs=("account_id", "limit"),
        execution_mode=SkillExecutionMode.READ_ONLY,
        required_permissions=(
            SkillPermission(action=PermissionAction.READ, object_type="account"),
            SkillPermission(action=PermissionAction.READ, object_type="opportunity"),
        ),
    ),
)


def crm_skill_descriptors() -> tuple[SkillDescriptor, ...]:
    """Return supported CRM Skill descriptors."""

    return CRM_SKILL_DESCRIPTORS


def run_crm_skill(
    name: str,
    repo_root: Path,
    user: User,
    policy_engine: PolicyEngine,
    inputs: Optional[Mapping[str, Any]] = None,
) -> SkillResult:
    """Run a CRM Skill handler."""

    descriptor = _descriptor_for(name)
    if descriptor is None:
        return SkillResult(
            name=name,
            decision=PolicyDecision.DENY,
            summary=f"Unknown CRM Skill: {name}",
            reasons=("Unknown CRM Skill.",),
        )

    authorization = _authorize_skill(user=user, policy_engine=policy_engine, descriptor=descriptor)
    if authorization is not None:
        return authorization

    values = dict(inputs or {})
    read_model = build_crm_read_model(repo_root)
    limit = _positive_int(values.get("limit"), default=5)

    if name == "pipeline-summary":
        return _pipeline_summary(read_model, limit)
    if name == "renewal-health":
        return _renewal_health(read_model.accounts, limit)
    if name == "opportunity-view":
        return _opportunity_view(
            opportunities=read_model.opportunities,
            account_id=str(values.get("account_id", "") or ""),
            limit=limit,
        )

    return SkillResult(
        name=name,
        decision=PolicyDecision.DENY,
        summary=f"CRM Skill is not implemented: {name}",
        reasons=("CRM Skill is not implemented.",),
    )


def _pipeline_summary(read_model, limit: int) -> SkillResult:
    top_opportunities = sorted(
        _open_opportunities(read_model.opportunities),
        key=lambda opportunity: (
            -opportunity.weighted_amount,
            opportunity.close_date,
            opportunity.id,
        ),
    )[:limit]
    summary = read_model.summary
    return SkillResult(
        name="pipeline-summary",
        decision=PolicyDecision.ALLOW,
        summary=(
            f"{summary.account_count} accounts, {summary.opportunity_count} opportunities, "
            f"{summary.open_pipeline_amount} open pipeline, "
            f"{summary.weighted_pipeline_amount} weighted pipeline."
        ),
        data={
            "summary": to_plain_data(summary),
            "top_opportunities": to_plain_data(top_opportunities),
        },
    )


def _renewal_health(
    accounts: tuple[CRMAccountReadRow, ...],
    limit: int,
) -> SkillResult:
    flagged_accounts = tuple(
        account
        for account in accounts
        if account.stage in ("renewal_due", "renewal_proposal")
        or account.health in ("yellow", "red")
    )
    sorted_accounts = sorted(
        flagged_accounts,
        key=lambda account: (account.renewal_date, account.health, account.id),
    )[:limit]
    return SkillResult(
        name="renewal-health",
        decision=PolicyDecision.ALLOW,
        summary=f"{len(flagged_accounts)} renewal or at-risk accounts need attention.",
        data={"accounts": to_plain_data(sorted_accounts)},
    )


def _opportunity_view(
    opportunities: tuple[CRMOpportunityReadRow, ...],
    account_id: str,
    limit: int,
) -> SkillResult:
    rows = _open_opportunities(opportunities)
    if account_id:
        rows = tuple(opportunity for opportunity in rows if opportunity.account_id == account_id)
    sorted_rows = sorted(
        rows,
        key=lambda row: (row.close_date, -row.weighted_amount, row.id),
    )[:limit]
    total_amount = sum(opportunity.amount for opportunity in sorted_rows)
    weighted_amount = sum(opportunity.weighted_amount for opportunity in sorted_rows)
    return SkillResult(
        name="opportunity-view",
        decision=PolicyDecision.ALLOW,
        summary=(
            f"{len(sorted_rows)} open opportunities"
            f" totaling {total_amount}, weighted {weighted_amount}."
        ),
        data={
            "account_id": account_id,
            "opportunities": to_plain_data(sorted_rows),
            "total_amount": total_amount,
            "weighted_amount": weighted_amount,
        },
    )


def _open_opportunities(
    opportunities: tuple[CRMOpportunityReadRow, ...],
) -> tuple[CRMOpportunityReadRow, ...]:
    return tuple(
        opportunity
        for opportunity in opportunities
        if opportunity.stage
        not in (
            "closed_won",
            "closed_lost",
            "renewed",
            "churned",
        )
    )


def _authorize_skill(
    user: User,
    policy_engine: PolicyEngine,
    descriptor: SkillDescriptor,
) -> Optional[SkillResult]:
    for permission in descriptor.required_permissions:
        result = policy_engine.evaluate(
            user=user,
            action=permission.action,
            obj={
                "id": f"{permission.object_type}_read_model",
                "object_type": permission.object_type,
                "owner": "",
            },
        )
        if result.decision != PolicyDecision.ALLOW:
            return SkillResult(
                name=descriptor.name,
                decision=PolicyDecision.DENY,
                summary="Skill request denied by policy.",
                reasons=tuple(
                    f"{permission.object_type}: {reason}" for reason in result.reasons
                ),
            )
    return None


def _descriptor_for(name: str) -> Optional[SkillDescriptor]:
    for descriptor in CRM_SKILL_DESCRIPTORS:
        if descriptor.name == name:
            return descriptor
    return None


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
