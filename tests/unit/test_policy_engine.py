"""Policy engine tests."""

from datetime import datetime, timezone
import unittest

from company_os_core import (
    BaseObject,
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    approval_required,
)


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class PolicyEngineTests(unittest.TestCase):
    def test_policy_allows_permitted_change_without_approval_rule(self) -> None:
        engine = self._engine()

        result = engine.evaluate(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.UPDATE,
            obj=self._account(),
            fields=("status",),
        )

        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_policy_requires_approval_for_controlled_field(self) -> None:
        engine = self._engine()

        result = engine.evaluate(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.UPDATE,
            obj=self._account(),
            fields=("metadata",),
        )

        self.assertEqual(result.decision, PolicyDecision.REQUIRES_APPROVAL)
        self.assertEqual(result.required_approvers, ("sales_manager", "finance"))
        self.assertEqual(result.reasons, ("Account metadata changes require approval.",))

    def test_policy_denies_when_rbac_denies(self) -> None:
        engine = self._engine()

        result = engine.evaluate(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.DELETE,
            obj=self._account(),
        )

        self.assertEqual(result.decision, PolicyDecision.DENY)
        self.assertEqual(result.reasons, ("No matching permission.",))

    def _engine(self) -> PolicyEngine:
        role = Role(
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
        rbac = RBACEngine(roles=(role,))
        return PolicyEngine(
            rbac=rbac,
            approval_rules=(
                approval_required(
                    object_type="account",
                    action=PermissionAction.UPDATE,
                    fields=("metadata",),
                    required_approvers=("sales_manager", "finance"),
                    reason="Account metadata changes require approval.",
                    rule_id="account_metadata_approval",
                ),
            ),
        )

    def _account(self) -> BaseObject:
        return BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
        )


if __name__ == "__main__":
    unittest.main()
