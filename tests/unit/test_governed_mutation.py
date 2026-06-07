"""Governed mutation service tests."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AuditEventWriter,
    BaseObject,
    GovernedMutationService,
    LocalObjectStore,
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    approval_required,
)
from company_os_core.schema import base_object_schema


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class GovernedMutationTests(unittest.TestCase):
    def test_allowed_create_stores_object_and_writes_completed_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service, store, audit = self._service(Path(temp_dir))

            result = service.create_object(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                obj=self._account(owner="ssabbani"),
                schema=base_object_schema("account"),
                request_id="req_create",
            )

            self.assertTrue(result.committed)
            self.assertEqual(result.policy_result.decision, PolicyDecision.ALLOW)
            self.assertEqual(store.list_object_ids("account"), ("acct_acme",))
            self.assertEqual(audit.list_event_ids(), (result.audit_event.event.event_id,))
            self.assertEqual(result.audit_event.event.result.value, "completed")

    def test_denied_create_does_not_store_object_but_writes_blocked_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service, store, audit = self._service(Path(temp_dir))

            result = service.create_object(
                user=User(id="viewer", username="viewer", roles=()),
                obj=self._account(owner="ssabbani"),
                schema=base_object_schema("account"),
                request_id="req_denied",
            )

            self.assertFalse(result.committed)
            self.assertEqual(result.policy_result.decision, PolicyDecision.DENY)
            self.assertEqual(store.list_object_ids("account"), ())
            self.assertEqual(audit.list_event_ids(), (result.audit_event.event.event_id,))
            self.assertEqual(result.audit_event.event.result.value, "blocked")

    def test_update_requiring_approval_does_not_store_but_writes_approval_audit(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service, store, audit = self._service(Path(temp_dir))
            original = self._account(owner="ssabbani")
            store.write_object(original, schema=base_object_schema("account"))
            before = store.read_object("account", "acct_acme").data
            after = self._account(owner="ssabbani", metadata={"industry": "robotics"})

            result = service.update_object(
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
                before=before,
                after=after,
                schema=base_object_schema("account"),
                fields=("metadata",),
                request_id="req_approval",
            )

            self.assertFalse(result.committed)
            self.assertEqual(result.policy_result.decision, PolicyDecision.REQUIRES_APPROVAL)
            self.assertEqual(result.policy_result.required_approvers, ("sales_manager",))
            self.assertEqual(audit.list_event_ids(), (result.audit_event.event.event_id,))
            self.assertEqual(result.audit_event.event.result.value, "requires_approval")
            self.assertEqual(store.read_object("account", "acct_acme").data["metadata"], {})

    def test_invalid_object_does_not_store_but_writes_failed_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            service, store, audit = self._service(Path(temp_dir))

            result = service.create_object(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                obj=BaseObject(
                    id="defect_acme",
                    object_type="defect",
                    owner="ssabbani",
                    created_at=TIMESTAMP,
                    updated_at=TIMESTAMP,
                    created_by="ssabbani",
                    updated_by="ssabbani",
                ),
                schema=base_object_schema("account"),
                request_id="req_invalid",
            )

            self.assertFalse(result.committed)
            self.assertEqual(result.policy_result.decision, PolicyDecision.DENY)
            self.assertFalse(result.validation_result.valid)
            self.assertEqual(store.list_object_ids("account"), ())
            self.assertEqual(audit.list_event_ids(), (result.audit_event.event.event_id,))
            self.assertEqual(result.audit_event.event.result.value, "failed")

    def _service(self, root: Path):
        store = LocalObjectStore(root, path_map={"account": "modules/crm/objects/accounts"})
        audit = AuditEventWriter(root / "platform/audit/events")
        founder = Role(
            id="founder",
            name="Founder",
            permissions=(
                Permission(
                    subject="founder",
                    action=PermissionAction.ALL,
                    object_type="*",
                    scope="company",
                ),
            ),
        )
        sales_rep = Role(
            id="sales_rep",
            name="Sales Rep",
            permissions=(
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.UPDATE,
                    object_type="account",
                    scope="owned_by_me",
                    fields=("status", "metadata"),
                ),
            ),
        )
        policy = PolicyEngine(
            rbac=RBACEngine(roles=(founder, sales_rep)),
            approval_rules=(
                approval_required(
                    object_type="account",
                    action=PermissionAction.UPDATE,
                    fields=("metadata",),
                    required_approvers=("sales_manager",),
                    reason="Account metadata changes require approval.",
                ),
            ),
        )
        return GovernedMutationService(store, policy, audit), store, audit

    def _account(
        self,
        owner: str,
        version: int = 1,
        metadata=None,
    ) -> BaseObject:
        return BaseObject(
            id="acct_acme",
            object_type="account",
            owner=owner,
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
            version=version,
            metadata=metadata or {},
        )


if __name__ == "__main__":
    unittest.main()
