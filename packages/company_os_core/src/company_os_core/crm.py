"""CRM module models and schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional

from company_os_core.models import ObjectLink, ObjectStatus, ObjectVisibility, PermissionAction
from company_os_core.schema import (
    FieldSchema,
    FieldType,
    ObjectSchema,
    ValidationIssue,
    ValidationResult,
    base_object_schema,
    extend_schema,
)


class AccountStage(str, Enum):
    """CRM account lifecycle stage."""

    LEAD = "lead"
    QUALIFIED = "qualified"
    ACTIVE_CUSTOMER = "active_customer"
    RENEWAL_DUE = "renewal_due"
    RENEWAL_PROPOSAL = "renewal_proposal"
    RENEWED = "renewed"
    CHURNED = "churned"


class CustomerHealth(str, Enum):
    """Customer health status."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class OpportunityStage(str, Enum):
    """CRM opportunity lifecycle stage."""

    LEAD = "lead"
    QUALIFIED = "qualified"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    RENEWAL_DUE = "renewal_due"
    RENEWAL_PROPOSAL = "renewal_proposal"
    RENEWED = "renewed"
    CHURNED = "churned"


class ApprovalStatus(str, Enum):
    """Approval status for CRM-controlled changes."""

    NOT_REQUIRED = "not_required"
    PENDING_MANAGER = "pending_manager"
    PENDING_FINANCE = "pending_finance"
    APPROVED = "approved"
    REJECTED = "rejected"


ACCOUNT_STAGE_TRANSITIONS: Mapping[AccountStage, tuple[AccountStage, ...]] = {
    AccountStage.LEAD: (AccountStage.QUALIFIED, AccountStage.CHURNED),
    AccountStage.QUALIFIED: (AccountStage.ACTIVE_CUSTOMER, AccountStage.CHURNED),
    AccountStage.ACTIVE_CUSTOMER: (AccountStage.RENEWAL_DUE, AccountStage.CHURNED),
    AccountStage.RENEWAL_DUE: (
        AccountStage.RENEWAL_PROPOSAL,
        AccountStage.RENEWED,
        AccountStage.CHURNED,
    ),
    AccountStage.RENEWAL_PROPOSAL: (AccountStage.RENEWED, AccountStage.CHURNED),
    AccountStage.RENEWED: (AccountStage.ACTIVE_CUSTOMER, AccountStage.RENEWAL_DUE),
    AccountStage.CHURNED: (),
}


OPPORTUNITY_STAGE_TRANSITIONS: Mapping[OpportunityStage, tuple[OpportunityStage, ...]] = {
    OpportunityStage.LEAD: (OpportunityStage.QUALIFIED, OpportunityStage.CLOSED_LOST),
    OpportunityStage.QUALIFIED: (
        OpportunityStage.DISCOVERY,
        OpportunityStage.PROPOSAL,
        OpportunityStage.CLOSED_LOST,
    ),
    OpportunityStage.DISCOVERY: (OpportunityStage.PROPOSAL, OpportunityStage.CLOSED_LOST),
    OpportunityStage.PROPOSAL: (OpportunityStage.NEGOTIATION, OpportunityStage.CLOSED_LOST),
    OpportunityStage.NEGOTIATION: (OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST),
    OpportunityStage.CLOSED_WON: (),
    OpportunityStage.CLOSED_LOST: (),
    OpportunityStage.RENEWAL_DUE: (OpportunityStage.RENEWAL_PROPOSAL, OpportunityStage.CHURNED),
    OpportunityStage.RENEWAL_PROPOSAL: (OpportunityStage.RENEWED, OpportunityStage.CHURNED),
    OpportunityStage.RENEWED: (),
    OpportunityStage.CHURNED: (),
}


@dataclass(frozen=True)
class CRMAccount:
    """CRM account source-of-truth object."""

    id: str
    owner: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    name: str
    stage: AccountStage
    industry: str
    arr: int
    health: CustomerHealth
    renewal_date: str
    object_type: str = "account"
    version: int = 1
    status: ObjectStatus = ObjectStatus.ACTIVE
    visibility: ObjectVisibility = ObjectVisibility.COMPANY
    links: tuple[ObjectLink, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CRMOpportunity:
    """CRM opportunity source-of-truth object."""

    id: str
    owner: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    account_id: str
    stage: OpportunityStage
    amount: int
    probability: float
    close_date: str
    discount_requested: int
    next_step: str
    approval_status: ApprovalStatus
    object_type: str = "opportunity"
    version: int = 1
    status: ObjectStatus = ObjectStatus.ACTIVE
    visibility: ObjectVisibility = ObjectVisibility.COMPANY
    links: tuple[ObjectLink, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


def account_schema() -> ObjectSchema:
    """Return the CRM account schema."""

    return extend_schema(
        base_object_schema("account"),
        (
            FieldSchema("name", FieldType.STRING),
            FieldSchema(
                "stage",
                FieldType.STRING,
                allowed_values=tuple(stage.value for stage in AccountStage),
            ),
            FieldSchema("industry", FieldType.STRING),
            FieldSchema("arr", FieldType.INTEGER, min_value=0),
            FieldSchema(
                "health",
                FieldType.STRING,
                allowed_values=tuple(health.value for health in CustomerHealth),
            ),
            FieldSchema("renewal_date", FieldType.DATE),
        ),
    )


def opportunity_schema() -> ObjectSchema:
    """Return the CRM opportunity schema."""

    return extend_schema(
        base_object_schema("opportunity"),
        (
            FieldSchema("account_id", FieldType.STRING),
            FieldSchema(
                "stage",
                FieldType.STRING,
                allowed_values=tuple(stage.value for stage in OpportunityStage),
            ),
            FieldSchema("amount", FieldType.INTEGER, min_value=0),
            FieldSchema("probability", FieldType.NUMBER, min_value=0, max_value=1),
            FieldSchema("close_date", FieldType.DATE),
            FieldSchema("discount_requested", FieldType.INTEGER, min_value=0, max_value=100),
            FieldSchema("next_step", FieldType.STRING),
            FieldSchema(
                "approval_status",
                FieldType.STRING,
                allowed_values=tuple(status.value for status in ApprovalStatus),
            ),
        ),
    )


def crm_lifecycle_validator(
    before: Optional[Mapping[str, Any]],
    after: Mapping[str, Any],
    action: PermissionAction,
) -> ValidationResult:
    """Validate CRM lifecycle transitions for governed mutations."""

    if action != PermissionAction.UPDATE or not before:
        return ValidationResult.ok()

    object_type = str(after.get("object_type", ""))
    if object_type == "account":
        return validate_account_stage_transition(before, after)
    if object_type == "opportunity":
        return validate_opportunity_stage_transition(before, after)
    return ValidationResult.ok()


def validate_account_stage_transition(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> ValidationResult:
    """Validate an account stage transition."""

    return _validate_stage_transition(
        before=before,
        after=after,
        enum_type=AccountStage,
        transitions=ACCOUNT_STAGE_TRANSITIONS,
        label="account",
    )


def validate_opportunity_stage_transition(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> ValidationResult:
    """Validate an opportunity stage transition."""

    return _validate_stage_transition(
        before=before,
        after=after,
        enum_type=OpportunityStage,
        transitions=OPPORTUNITY_STAGE_TRANSITIONS,
        label="opportunity",
    )


def _validate_stage_transition(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    enum_type,
    transitions: Mapping[Any, tuple[Any, ...]],
    label: str,
) -> ValidationResult:
    before_stage = _stage_from_data(before, enum_type, label, "before.stage")
    after_stage = _stage_from_data(after, enum_type, label, "stage")
    issues = [
        issue
        for value, issue in (before_stage, after_stage)
        if value is None and issue is not None
    ]
    if issues:
        return ValidationResult.failed(issues)

    from_stage = before_stage[0]
    to_stage = after_stage[0]
    if from_stage == to_stage:
        return ValidationResult.ok()

    allowed = transitions.get(from_stage, ())
    if to_stage in allowed:
        return ValidationResult.ok()

    allowed_values = ", ".join(stage.value for stage in allowed) or "none"
    return ValidationResult.failed(
        [
            ValidationIssue(
                field="stage",
                message=(
                    f"invalid {label} stage transition: {from_stage.value} -> {to_stage.value}; "
                    f"allowed next stages: {allowed_values}"
                ),
            )
        ]
    )


def _stage_from_data(data: Mapping[str, Any], enum_type, label: str, field: str):
    value = str(data.get("stage", ""))
    try:
        return enum_type(value), None
    except ValueError:
        return None, ValidationIssue(field=field, message=f"unknown {label} stage: {value}")
