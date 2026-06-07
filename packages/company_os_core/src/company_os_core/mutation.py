"""Governed mutation service for opra.ai."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from company_os_core.audit import AuditEventWriter, WrittenAuditEvent
from company_os_core.models import (
    AuditAction,
    BaseObject,
    EventResult,
    PermissionAction,
    PolicyDecision,
    PolicyResult,
    SourceInterface,
    User,
)
from company_os_core.object_store import LocalObjectStore, StoredObject
from company_os_core.policy import PolicyEngine
from company_os_core.schema import ObjectSchema, ValidationResult, validate_object
from company_os_core.serialization import to_plain_data


DomainValidator = Callable[
    [Optional[Mapping[str, Any]], Mapping[str, Any], PermissionAction],
    ValidationResult,
]


@dataclass(frozen=True)
class MutationResult:
    """Result of a governed source-of-truth mutation."""

    policy_result: PolicyResult
    validation_result: ValidationResult
    audit_event: WrittenAuditEvent
    stored_object: Optional[StoredObject] = None

    @property
    def committed(self) -> bool:
        return self.stored_object is not None


class GovernedMutationService:
    """Apply validation, policy, storage, and audit in one path."""

    def __init__(
        self,
        object_store: LocalObjectStore,
        policy_engine: PolicyEngine,
        audit_writer: AuditEventWriter,
        domain_validators: tuple[DomainValidator, ...] = (),
    ) -> None:
        self._object_store = object_store
        self._policy_engine = policy_engine
        self._audit_writer = audit_writer
        self._domain_validators = domain_validators

    def create_object(
        self,
        user: User,
        obj: BaseObject,
        schema: ObjectSchema,
        request_id: str,
        source_interface: SourceInterface = SourceInterface.CLI,
    ) -> MutationResult:
        return self._mutate(
            user=user,
            action=PermissionAction.CREATE,
            audit_action=AuditAction.CREATE,
            before=None,
            after=obj,
            schema=schema,
            fields=(),
            request_id=request_id,
            source_interface=source_interface,
        )

    def update_object(
        self,
        user: User,
        before: Mapping[str, Any],
        after: BaseObject,
        schema: ObjectSchema,
        fields: tuple[str, ...],
        request_id: str,
        source_interface: SourceInterface = SourceInterface.CLI,
    ) -> MutationResult:
        return self._mutate(
            user=user,
            action=PermissionAction.UPDATE,
            audit_action=AuditAction.UPDATE,
            before=before,
            after=after,
            schema=schema,
            fields=fields,
            request_id=request_id,
            source_interface=source_interface,
        )

    def _mutate(
        self,
        user: User,
        action: PermissionAction,
        audit_action: AuditAction,
        before: Optional[Mapping[str, Any]],
        after: BaseObject,
        schema: ObjectSchema,
        fields: tuple[str, ...],
        request_id: str,
        source_interface: SourceInterface,
    ) -> MutationResult:
        after_data = to_plain_data(after)
        validation_result = validate_object(after_data, schema)
        if not validation_result.valid:
            policy_result = PolicyResult(
                decision=PolicyDecision.DENY,
                reasons=tuple(
                    f"{issue.field}: {issue.message}" for issue in validation_result.issues
                ),
            )
            audit_event = self._write_audit(
                user=user,
                audit_action=audit_action,
                after=after_data,
                before=before,
                result=EventResult.FAILED,
                request_id=request_id,
                source_interface=source_interface,
            )
            return MutationResult(
                policy_result=policy_result,
                validation_result=validation_result,
                audit_event=audit_event,
            )

        domain_result = self._validate_domain(
            before=before,
            after=after_data,
            action=action,
        )
        if not domain_result.valid:
            policy_result = PolicyResult(
                decision=PolicyDecision.DENY,
                reasons=tuple(
                    f"{issue.field}: {issue.message}" for issue in domain_result.issues
                ),
            )
            audit_event = self._write_audit(
                user=user,
                audit_action=audit_action,
                after=after_data,
                before=before,
                result=EventResult.FAILED,
                request_id=request_id,
                source_interface=source_interface,
            )
            return MutationResult(
                policy_result=policy_result,
                validation_result=domain_result,
                audit_event=audit_event,
            )

        policy_result = self._policy_engine.evaluate(
            user=user,
            action=action,
            obj=after_data,
            fields=fields,
        )
        if policy_result.decision == PolicyDecision.DENY:
            audit_event = self._write_audit(
                user=user,
                audit_action=audit_action,
                before=before,
                after=after_data,
                result=EventResult.BLOCKED,
                request_id=request_id,
                source_interface=source_interface,
            )
            return MutationResult(
                policy_result=policy_result,
                validation_result=validation_result,
                audit_event=audit_event,
            )

        if policy_result.decision == PolicyDecision.REQUIRES_APPROVAL:
            audit_event = self._write_audit(
                user=user,
                audit_action=audit_action,
                before=before,
                after=after_data,
                result=EventResult.REQUIRES_APPROVAL,
                request_id=request_id,
                source_interface=source_interface,
            )
            return MutationResult(
                policy_result=policy_result,
                validation_result=validation_result,
                audit_event=audit_event,
            )

        stored_object = self._object_store.write_object(after, schema=schema)
        audit_event = self._write_audit(
            user=user,
            audit_action=audit_action,
            before=before,
            after=after_data,
            result=EventResult.COMPLETED,
            request_id=request_id,
            source_interface=source_interface,
        )
        return MutationResult(
            policy_result=policy_result,
            validation_result=validation_result,
            audit_event=audit_event,
            stored_object=stored_object,
        )

    def _write_audit(
        self,
        user: User,
        audit_action: AuditAction,
        before: Optional[Mapping[str, Any]],
        after: Mapping[str, Any],
        result: EventResult,
        request_id: str,
        source_interface: SourceInterface,
    ) -> WrittenAuditEvent:
        return self._audit_writer.record_mutation(
            actor=user.username,
            action=audit_action,
            object_type=str(after["object_type"]),
            object_id=str(after["id"]),
            source_interface=source_interface,
            request_id=request_id,
            before=before,
            after=after,
            result=result,
        )

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
