"""Audit event writer tests."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AuditAction,
    AuditEventWriter,
    BaseObject,
    EventResult,
    SourceInterface,
)
from company_os_core.serialization import stable_hash


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class AuditEventWriterTests(unittest.TestCase):
    def test_records_create_event_with_after_hash(self) -> None:
        with TemporaryDirectory() as temp_dir:
            event_dir = Path(temp_dir) / "platform/audit/events"
            account = self._account(owner="ssabbani")

            written = AuditEventWriter(event_dir).record_mutation(
                actor="ssabbani",
                action=AuditAction.CREATE,
                object_type="account",
                object_id="acct_acme",
                source_interface=SourceInterface.CLI,
                request_id="req_001",
                after=account,
                timestamp=TIMESTAMP,
                event_id="evt_create_acme",
            )

            self.assertEqual(written.path, event_dir / "evt_create_acme.yaml")
            self.assertTrue(written.path.exists())
            self.assertIsNone(written.event.before_hash)
            self.assertEqual(written.event.after_hash, stable_hash(account))

            data = AuditEventWriter(event_dir).read_event("evt_create_acme")
            self.assertEqual(data["event_id"], "evt_create_acme")
            self.assertEqual(data["action"], "create")
            self.assertEqual(data["source"]["interface"], "cli")
            self.assertNotIn("before_hash", data)
            self.assertEqual(data["after_hash"], stable_hash(account))

    def test_records_update_event_with_before_and_after_hashes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            event_dir = Path(temp_dir) / "platform/audit/events"
            before = self._account(owner="ssabbani")
            after = self._account(owner="new_owner")

            written = AuditEventWriter(event_dir).record_mutation(
                actor="ssabbani",
                action=AuditAction.UPDATE,
                object_type="account",
                object_id="acct_acme",
                source_interface=SourceInterface.API,
                request_id="req_002",
                before=before,
                after=after,
                result=EventResult.REQUIRES_APPROVAL,
                timestamp=TIMESTAMP,
                event_id="evt_update_acme",
            )

            self.assertEqual(written.event.before_hash, stable_hash(before))
            self.assertEqual(written.event.after_hash, stable_hash(after))
            self.assertEqual(written.event.result, EventResult.REQUIRES_APPROVAL)

    def test_writer_is_append_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            writer = AuditEventWriter(Path(temp_dir))

            writer.record_mutation(
                actor="ssabbani",
                action=AuditAction.CREATE,
                object_type="account",
                object_id="acct_acme",
                source_interface=SourceInterface.CLI,
                request_id="req_001",
                after=self._account(owner="ssabbani"),
                event_id="evt_duplicate",
                timestamp=TIMESTAMP,
            )

            with self.assertRaises(FileExistsError):
                writer.record_mutation(
                    actor="ssabbani",
                    action=AuditAction.UPDATE,
                    object_type="account",
                    object_id="acct_acme",
                    source_interface=SourceInterface.CLI,
                    request_id="req_002",
                    after=self._account(owner="ssabbani"),
                    event_id="evt_duplicate",
                    timestamp=TIMESTAMP,
                )

    def test_lists_event_ids(self) -> None:
        with TemporaryDirectory() as temp_dir:
            writer = AuditEventWriter(Path(temp_dir))
            for event_id in ("evt_b", "evt_a"):
                writer.record_mutation(
                    actor="ssabbani",
                    action=AuditAction.CREATE,
                    object_type="account",
                    object_id=event_id,
                    source_interface=SourceInterface.CLI,
                    request_id=event_id,
                    after=self._account(owner="ssabbani"),
                    event_id=event_id,
                    timestamp=TIMESTAMP,
                )

            self.assertEqual(writer.list_event_ids(), ("evt_a", "evt_b"))

    def _account(self, owner: str) -> BaseObject:
        return BaseObject(
            id="acct_acme",
            object_type="account",
            owner=owner,
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
        )


if __name__ == "__main__":
    unittest.main()
