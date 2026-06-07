"""Core domain model tests."""

from datetime import datetime, timezone
import unittest

from company_os_core import (
    AuditAction,
    AuditEvent,
    BaseObject,
    EventResult,
    EventSource,
    ObjectLink,
    ObjectStatus,
    ObjectVisibility,
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyResult,
    Role,
    SourceInterface,
    User,
)
from company_os_core.serialization import to_plain_data, to_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class CoreModelTests(unittest.TestCase):
    def test_base_object_contract_serializes_to_plain_data(self) -> None:
        account = BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            visibility=ObjectVisibility.COMPANY,
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
            links=(
                ObjectLink(
                    target_type="opportunity",
                    target_id="opp_acme_renewal",
                    relationship="has_opportunity",
                ),
            ),
            tags=("design_partner", "strategic"),
            metadata={"industry": "manufacturing"},
        )

        plain = to_plain_data(account)

        self.assertEqual(plain["id"], "acct_acme")
        self.assertEqual(plain["object_type"], "account")
        self.assertEqual(plain["version"], 1)
        self.assertEqual(plain["status"], "active")
        self.assertEqual(plain["visibility"], "company")
        self.assertEqual(plain["created_at"], "2026-06-06T10:00:00Z")
        self.assertEqual(plain["links"][0]["target_id"], "opp_acme_renewal")
        self.assertEqual(plain["metadata"]["industry"], "manufacturing")

    def test_base_object_rejects_missing_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must be a non-empty string"):
            BaseObject(
                id="",
                object_type="account",
                owner="ssabbani",
                created_at=TIMESTAMP,
                updated_at=TIMESTAMP,
                created_by="ssabbani",
                updated_by="ssabbani",
            )

    def test_base_object_rejects_naive_datetime(self) -> None:
        with self.assertRaisesRegex(ValueError, "created_at must include timezone"):
            BaseObject(
                id="acct_acme",
                object_type="account",
                owner="ssabbani",
                created_at=datetime(2026, 6, 6, 10, 0, 0),
                updated_at=TIMESTAMP,
                created_by="ssabbani",
                updated_by="ssabbani",
            )

    def test_audit_event_contract_serializes_source_and_result(self) -> None:
        event = AuditEvent(
            event_id="evt_001",
            timestamp=TIMESTAMP,
            actor="ssabbani",
            action=AuditAction.UPDATE,
            object_type="opportunity",
            object_id="opp_acme_renewal",
            before_hash="abc123",
            after_hash="def456",
            source=EventSource(interface=SourceInterface.SKILL, request_id="req_001"),
            result=EventResult.COMPLETED,
        )

        plain = to_plain_data(event)

        self.assertEqual(plain["action"], "update")
        self.assertEqual(plain["source"]["interface"], "skill")
        self.assertEqual(plain["source"]["request_id"], "req_001")
        self.assertEqual(plain["result"], "completed")

    def test_user_role_permission_and_policy_result_contracts(self) -> None:
        permission = Permission(
            subject="sales_rep",
            action=PermissionAction.UPDATE,
            object_type="opportunity",
            scope="owned_by_me",
            fields=("stage", "probability", "next_step"),
        )
        role = Role(id="sales_rep", name="Sales Rep", permissions=(permission,))
        user = User(id="usr_suman", username="ssabbani", roles=("sales_rep",))
        result = PolicyResult(
            decision=PolicyDecision.REQUIRES_APPROVAL,
            reasons=("Discount above threshold.",),
            required_approvers=("finance",),
            matched_permissions=("sales_rep:update:opportunity",),
        )

        self.assertEqual(to_plain_data(role)["permissions"][0]["action"], "update")
        self.assertEqual(to_plain_data(user)["roles"], ["sales_rep"])
        self.assertEqual(to_plain_data(result)["decision"], "requires_approval")
        self.assertEqual(to_plain_data(result)["required_approvers"], ["finance"])

    def test_yaml_output_is_deterministic_and_human_readable(self) -> None:
        account = BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
            tags=("design_partner", "strategic"),
        )

        self.assertEqual(
            to_yaml(account),
            "\n".join(
                [
                    "id: acct_acme",
                    "object_type: account",
                    "owner: ssabbani",
                    "created_by: ssabbani",
                    "updated_by: ssabbani",
                    "created_at: 2026-06-06T10:00:00Z",
                    "updated_at: 2026-06-06T10:00:00Z",
                    "version: 1",
                    "status: active",
                    "visibility: company",
                    "links: []",
                    "tags:",
                    "  - design_partner",
                    "  - strategic",
                    "metadata: {}",
                    "",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
