"""Mutation proposal artifacts for review workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

from company_os_core.audit import AuditEventWriter, WrittenAuditEvent
from company_os_core.models import (
    ApprovalDecision,
    AuditAction,
    BaseObject,
    EventResult,
    PermissionAction,
    PolicyDecision,
    PolicyResult,
    SourceInterface,
    User,
    utc_now,
)
from company_os_core.mutation import DomainValidator
from company_os_core.object_store import LocalObjectStore
from company_os_core.policy import PolicyEngine
from company_os_core.schema import ObjectSchema, ValidationResult, validate_object
from company_os_core.serialization import read_yaml, stable_hash, to_plain_data, write_yaml


DEFAULT_MUTATION_PROPOSAL_DIR = Path("platform/proposals/mutations")
APPROVED_DECISION = "approved"
REJECTED_DECISION = "rejected"


class MutationProposalStatus(str, Enum):
    """Lifecycle status for mutation proposal artifacts."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass(frozen=True)
class MutationProposalApproval:
    """One approval or rejection recorded against a mutation proposal."""

    approver: str
    decision: str
    timestamp: datetime
    subjects: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""


@dataclass(frozen=True)
class MutationProposal:
    """Reviewable proposal for a source-of-truth mutation."""

    id: str
    status: MutationProposalStatus
    created_at: datetime
    created_by: str
    source_interface: SourceInterface
    request_id: str
    action: PermissionAction
    object_type: str
    object_id: str
    target_path: str
    fields: tuple[str, ...]
    policy_decision: PolicyDecision
    required_approvers: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    approvals: tuple[MutationProposalApproval, ...] = field(default_factory=tuple)
    before_hash: Optional[str] = None
    after_hash: str = ""
    before: Optional[Mapping[str, Any]] = None
    after: Mapping[str, Any] = field(default_factory=dict)
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: str = ""
    applied_at: Optional[datetime] = None
    applied_by: str = ""
    audit_event_id: str = ""


@dataclass(frozen=True)
class WrittenMutationProposal:
    """Mutation proposal artifact written to disk."""

    path: Path
    proposal: MutationProposal


@dataclass(frozen=True)
class AppliedMutationProposal:
    """Applied proposal, source target, and audit evidence."""

    proposal_path: Path
    proposal: MutationProposal
    target_path: Path
    audit_event: WrittenAuditEvent


class MutationProposalError(ValueError):
    """Raised when a mutation proposal cannot be created."""


class MutationProposalService:
    """Manage reviewable proposal artifacts without bypassing governance."""

    def __init__(
        self,
        repo_root: Path,
        object_store: LocalObjectStore,
        policy_engine: PolicyEngine,
        proposal_dir: Path = DEFAULT_MUTATION_PROPOSAL_DIR,
        domain_validators: tuple[DomainValidator, ...] = (),
    ) -> None:
        self._repo_root = repo_root
        self._object_store = object_store
        self._policy_engine = policy_engine
        self._proposal_dir = proposal_dir
        self._domain_validators = domain_validators

    def propose(
        self,
        user: User,
        action: PermissionAction,
        before: Optional[Mapping[str, Any]],
        after: BaseObject,
        schema: ObjectSchema,
        fields: tuple[str, ...],
        request_id: str,
        source_interface: SourceInterface = SourceInterface.CLI,
    ) -> WrittenMutationProposal:
        """Create a mutation proposal artifact."""

        if action == PermissionAction.UPDATE and not before:
            raise MutationProposalError("before state is required for update proposals")

        after_data = to_plain_data(after)
        validation_result = validate_object(after_data, schema)
        _raise_if_invalid("schema validation failed", validation_result)

        domain_result = self._validate_domain(before=before, after=after_data, action=action)
        _raise_if_invalid("domain validation failed", domain_result)

        policy_result = self._policy_engine.evaluate(
            user=user,
            action=action,
            obj=after_data,
            fields=fields,
        )
        if policy_result.decision == PolicyDecision.DENY:
            reasons = "; ".join(policy_result.reasons) or "policy denied proposal"
            raise MutationProposalError(f"policy denied proposal: {reasons}")

        proposal = self._proposal(
            user=user,
            action=action,
            before=before,
            after=after_data,
            policy_result=policy_result,
            fields=fields,
            request_id=request_id,
            source_interface=source_interface,
        )
        path = self._proposal_path(proposal.id)
        if path.exists():
            raise FileExistsError(f"Mutation proposal already exists: {path}")
        write_yaml(path, proposal)
        return WrittenMutationProposal(path=path, proposal=proposal)

    def read_proposal(self, path: Path) -> MutationProposal:
        """Read a mutation proposal artifact."""

        return _proposal_from_data(read_yaml(path))

    def approve(
        self,
        path: Path,
        user: User,
        reason: str = "",
    ) -> WrittenMutationProposal:
        """Record an approval and mark the proposal approved when requirements are met."""

        proposal = self.read_proposal(path)
        if proposal.status != MutationProposalStatus.PROPOSED:
            raise MutationProposalError(
                f"proposal {proposal.id} is not open for approval: {proposal.status.value}"
            )
        if not self._can_user_approve(proposal=proposal, user=user):
            raise MutationProposalError("user is not an allowed approver for this proposal")

        now = utc_now()
        approval = MutationProposalApproval(
            approver=user.username,
            decision=APPROVED_DECISION,
            timestamp=now,
            subjects=_user_subjects(user),
            reason=reason,
        )
        approvals = proposal.approvals + (approval,)
        status = (
            MutationProposalStatus.PROPOSED
            if self._unmet_required_approvers(proposal, approvals)
            else MutationProposalStatus.APPROVED
        )
        updated = replace(
            proposal,
            status=status,
            approvals=approvals,
            approved_at=now if status == MutationProposalStatus.APPROVED else None,
        )
        write_yaml(path, updated)
        return WrittenMutationProposal(path=path, proposal=updated)

    def reject(
        self,
        path: Path,
        user: User,
        reason: str = "",
    ) -> WrittenMutationProposal:
        """Reject an open mutation proposal."""

        proposal = self.read_proposal(path)
        if proposal.status != MutationProposalStatus.PROPOSED:
            raise MutationProposalError(
                f"proposal {proposal.id} is not open for rejection: {proposal.status.value}"
            )
        if not self._can_user_approve(proposal=proposal, user=user):
            raise MutationProposalError("user is not an allowed approver for this proposal")

        now = utc_now()
        rejection = MutationProposalApproval(
            approver=user.username,
            decision=REJECTED_DECISION,
            timestamp=now,
            subjects=_user_subjects(user),
            reason=reason,
        )
        updated = replace(
            proposal,
            status=MutationProposalStatus.REJECTED,
            approvals=proposal.approvals + (rejection,),
            rejected_at=now,
            rejection_reason=reason,
        )
        write_yaml(path, updated)
        return WrittenMutationProposal(path=path, proposal=updated)

    def apply(
        self,
        path: Path,
        user: User,
        schema: ObjectSchema,
        audit_writer: AuditEventWriter,
        source_interface: SourceInterface = SourceInterface.CLI,
    ) -> AppliedMutationProposal:
        """Apply an approved mutation proposal to the source object."""

        proposal = self.read_proposal(path)
        if proposal.status != MutationProposalStatus.APPROVED:
            raise MutationProposalError(
                f"proposal {proposal.id} must be approved before apply"
            )

        execute_result = self._policy_engine.evaluate(
            user=user,
            action=PermissionAction.EXECUTE,
            obj=proposal.after,
            fields=proposal.fields,
        )
        if execute_result.decision == PolicyDecision.DENY:
            reasons = "; ".join(execute_result.reasons)
            raise MutationProposalError(f"user is not authorized to apply proposal: {reasons}")

        if proposal.after_hash != stable_hash(proposal.after):
            raise MutationProposalError("proposal after_hash does not match after snapshot")

        before = self._current_before_state(proposal)
        validation_result = validate_object(proposal.after, schema)
        _raise_if_invalid("schema validation failed", validation_result)

        domain_result = self._validate_domain(
            before=before,
            after=proposal.after,
            action=proposal.action,
        )
        _raise_if_invalid("domain validation failed", domain_result)

        target_path = self._object_store.object_path(
            object_type=proposal.object_type,
            object_id=proposal.object_id,
        )
        write_yaml(target_path, proposal.after)
        audit_event = audit_writer.record_mutation(
            actor=user.username,
            action=_audit_action_for(proposal.action),
            object_type=proposal.object_type,
            object_id=proposal.object_id,
            source_interface=source_interface,
            request_id=proposal.request_id,
            before=before,
            after=proposal.after,
            result=EventResult.COMPLETED,
            approval_chain=_audit_approval_chain(proposal.approvals),
        )
        updated = replace(
            proposal,
            status=MutationProposalStatus.APPLIED,
            applied_at=utc_now(),
            applied_by=user.username,
            audit_event_id=audit_event.event.event_id,
        )
        write_yaml(path, updated)
        return AppliedMutationProposal(
            proposal_path=path,
            proposal=updated,
            target_path=target_path,
            audit_event=audit_event,
        )

    def remaining_approvers(self, proposal: MutationProposal) -> tuple[str, ...]:
        """Return required approver subjects that have not approved yet."""

        return self._unmet_required_approvers(proposal, proposal.approvals)

    def _proposal(
        self,
        user: User,
        action: PermissionAction,
        before: Optional[Mapping[str, Any]],
        after: Mapping[str, Any],
        policy_result: PolicyResult,
        fields: tuple[str, ...],
        request_id: str,
        source_interface: SourceInterface,
    ) -> MutationProposal:
        object_type = str(after["object_type"])
        object_id = str(after["id"])
        target_path = self._target_path(object_type=object_type, object_id=object_id)
        return MutationProposal(
            id=f"proposal_{_safe_id(request_id)}",
            status=MutationProposalStatus.PROPOSED,
            created_at=utc_now(),
            created_by=user.username,
            source_interface=source_interface,
            request_id=request_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            target_path=target_path,
            fields=fields,
            policy_decision=policy_result.decision,
            required_approvers=policy_result.required_approvers,
            reasons=policy_result.reasons,
            before_hash=stable_hash(before) if before is not None else None,
            after_hash=stable_hash(after),
            before=before,
            after=after,
        )

    def _target_path(self, object_type: str, object_id: str) -> str:
        path = self._object_store.object_path(object_type=object_type, object_id=object_id)
        try:
            return str(path.relative_to(self._repo_root))
        except ValueError:
            return str(path)

    def _proposal_path(self, proposal_id: str) -> Path:
        root = self._proposal_dir
        if not root.is_absolute():
            root = self._repo_root / root
        return root / f"{proposal_id}.yaml"

    def _can_user_approve(self, proposal: MutationProposal, user: User) -> bool:
        if proposal.required_approvers:
            return bool(set(proposal.required_approvers).intersection(_user_subjects(user)))

        result = self._policy_engine.evaluate(
            user=user,
            action=PermissionAction.APPROVE,
            obj=proposal.after,
            fields=proposal.fields,
        )
        return result.decision != PolicyDecision.DENY

    def _unmet_required_approvers(
        self,
        proposal: MutationProposal,
        approvals: tuple[MutationProposalApproval, ...],
    ) -> tuple[str, ...]:
        remaining = []
        approved_subjects = {
            subject
            for approval in approvals
            if approval.decision == APPROVED_DECISION
            for subject in approval.subjects
        }
        for required_approver in proposal.required_approvers:
            if required_approver not in approved_subjects:
                remaining.append(required_approver)
        return tuple(remaining)

    def _current_before_state(self, proposal: MutationProposal) -> Optional[Mapping[str, Any]]:
        target_path = self._object_store.object_path(
            object_type=proposal.object_type,
            object_id=proposal.object_id,
        )
        if proposal.action == PermissionAction.CREATE:
            if target_path.exists():
                raise MutationProposalError(f"target object already exists: {target_path}")
            return None

        if proposal.action != PermissionAction.UPDATE:
            raise MutationProposalError(f"unsupported proposal action: {proposal.action.value}")
        if proposal.before_hash is None:
            raise MutationProposalError("update proposal is missing before_hash")

        before = self._object_store.read_object(
            proposal.object_type,
            proposal.object_id,
        ).data
        if stable_hash(before) != proposal.before_hash:
            raise MutationProposalError("current object hash does not match proposal before_hash")
        return before

    def _validate_domain(
        self,
        before: Optional[Mapping[str, Any]],
        after: Mapping[str, Any],
        action: PermissionAction,
    ) -> ValidationResult:
        issues = []
        for validator in self._domain_validators:
            result = validator(before, after, action)
            if not result.valid:
                issues.extend(result.issues)

        if issues:
            return ValidationResult.failed(issues)
        return ValidationResult.ok()


def _raise_if_invalid(prefix: str, result: ValidationResult) -> None:
    if result.valid:
        return
    reasons = "; ".join(f"{issue.field}: {issue.message}" for issue in result.issues)
    raise MutationProposalError(f"{prefix}: {reasons}")


def _proposal_from_data(data: Any) -> MutationProposal:
    if not isinstance(data, Mapping):
        raise MutationProposalError("proposal file must contain a YAML object")

    before = data.get("before")
    after = data.get("after")
    return MutationProposal(
        id=str(data["id"]),
        status=MutationProposalStatus(str(data["status"])),
        created_at=_parse_utc_timestamp(str(data["created_at"])),
        created_by=str(data["created_by"]),
        source_interface=SourceInterface(str(data["source_interface"])),
        request_id=str(data["request_id"]),
        action=PermissionAction(str(data["action"])),
        object_type=str(data["object_type"]),
        object_id=str(data["object_id"]),
        target_path=str(data["target_path"]),
        fields=_string_tuple(data.get("fields", [])),
        policy_decision=PolicyDecision(str(data["policy_decision"])),
        required_approvers=_string_tuple(data.get("required_approvers", [])),
        reasons=_string_tuple(data.get("reasons", [])),
        approvals=_approvals_from_data(data.get("approvals", [])),
        before_hash=_optional_string(data.get("before_hash")),
        after_hash=str(data.get("after_hash", "")),
        before=_optional_mapping(before, "before"),
        after=_required_mapping(after, "after"),
        approved_at=_optional_timestamp(data.get("approved_at")),
        rejected_at=_optional_timestamp(data.get("rejected_at")),
        rejection_reason=str(data.get("rejection_reason", "")),
        applied_at=_optional_timestamp(data.get("applied_at")),
        applied_by=str(data.get("applied_by", "")),
        audit_event_id=str(data.get("audit_event_id", "")),
    )


def _approvals_from_data(value: Any) -> tuple[MutationProposalApproval, ...]:
    if value is None or value == {}:
        return ()
    if not isinstance(value, list):
        raise MutationProposalError("approvals must be a list")

    approvals = []
    for item in value:
        if not isinstance(item, Mapping):
            raise MutationProposalError("approval entry must be an object")
        approvals.append(
            MutationProposalApproval(
                approver=str(item["approver"]),
                decision=str(item["decision"]),
                timestamp=_parse_utc_timestamp(str(item["timestamp"])),
                subjects=_string_tuple(item.get("subjects", [])),
                reason=str(item.get("reason", "")),
            )
        )
    return tuple(approvals)


def _audit_approval_chain(
    approvals: tuple[MutationProposalApproval, ...],
) -> tuple[ApprovalDecision, ...]:
    return tuple(
        ApprovalDecision(
            approver=approval.approver,
            decision=approval.decision,
            timestamp=approval.timestamp,
        )
        for approval in approvals
    )


def _audit_action_for(action: PermissionAction) -> AuditAction:
    if action == PermissionAction.CREATE:
        return AuditAction.CREATE
    if action == PermissionAction.UPDATE:
        return AuditAction.UPDATE
    raise MutationProposalError(f"unsupported proposal action: {action.value}")


def _user_subjects(user: User) -> tuple[str, ...]:
    subjects = [user.id, user.username]
    subjects.extend(user.roles)
    subjects.extend(f"role:{role_id}" for role_id in user.roles)
    subjects.extend(user.teams)
    subjects.extend(f"team:{team_id}" for team_id in user.teams)
    return tuple(subjects)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == {}:
        return ()
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    raise MutationProposalError("expected a list of strings")


def _optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _required_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MutationProposalError(f"{field_name} must be an object")
    return value


def _optional_mapping(value: Any, field_name: str) -> Optional[Mapping[str, Any]]:
    if value is None:
        return None
    return _required_mapping(value, field_name)


def _optional_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    return _parse_utc_timestamp(str(value))


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _safe_id(value: str) -> str:
    if not value or not value.strip():
        raise MutationProposalError("request_id is required")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe.strip("._") or "proposal"
