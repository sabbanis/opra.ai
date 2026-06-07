"""Audit event writing for opra.ai."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional
from uuid import uuid4

from company_os_core.models import (
    ApprovalDecision,
    AuditAction,
    AuditEvent,
    EventResult,
    EventSource,
    SourceInterface,
    utc_now,
)
from company_os_core.serialization import read_yaml, stable_hash, write_yaml


@dataclass(frozen=True)
class WrittenAuditEvent:
    """Audit event plus the path it was written to."""

    event: AuditEvent
    path: Path


class AuditEventWriter:
    """Append-only audit event writer."""

    def __init__(self, event_dir: Path) -> None:
        self._event_dir = event_dir

    def event_path(self, event_id: str) -> Path:
        if not event_id or not event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        return self._event_dir / f"{event_id}.yaml"

    def record_mutation(
        self,
        actor: str,
        action: AuditAction,
        object_type: str,
        object_id: str,
        source_interface: SourceInterface,
        request_id: str,
        before: Optional[Any] = None,
        after: Optional[Any] = None,
        result: EventResult = EventResult.COMPLETED,
        approval_chain: tuple[ApprovalDecision, ...] = (),
        timestamp: Optional[datetime] = None,
        event_id: Optional[str] = None,
    ) -> WrittenAuditEvent:
        event = AuditEvent(
            event_id=event_id or _new_event_id(),
            timestamp=timestamp or utc_now(),
            actor=actor,
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_hash=_optional_hash(before),
            after_hash=_optional_hash(after),
            source=EventSource(interface=source_interface, request_id=request_id),
            result=result,
            approval_chain=approval_chain,
        )
        return self.write_event(event)

    def write_event(self, event: AuditEvent) -> WrittenAuditEvent:
        path = self.event_path(event.event_id)
        if path.exists():
            raise FileExistsError(f"Audit event already exists: {path}")

        write_yaml(path, event)
        return WrittenAuditEvent(event=event, path=path)

    def read_event(self, event_id: str) -> Mapping[str, Any]:
        data = read_yaml(self.event_path(event_id))
        if not isinstance(data, Mapping):
            raise ValueError(f"Audit event {event_id} is not a mapping")
        return data

    def list_event_ids(self) -> tuple[str, ...]:
        if not self._event_dir.exists():
            return ()
        return tuple(sorted(path.stem for path in self._event_dir.glob("*.yaml")))


def _optional_hash(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    return stable_hash(value)


def _new_event_id() -> str:
    return f"evt_{uuid4().hex}"
