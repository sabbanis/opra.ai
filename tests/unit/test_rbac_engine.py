"""RBAC engine tests."""

from datetime import datetime, timezone
import unittest

from company_os_core import (
    BaseObject,
    Permission,
    PermissionAction,
    PolicyDecision,
    RBACEngine,
    Role,
    User,
)


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class RBACEngineTests(unittest.TestCase):
    def test_role_permission_allows_company_read(self) -> None:
        engine = RBACEngine(
            roles=(
                Role(
                    id="sales_rep",
                    name="Sales Rep",
                    permissions=(
                        Permission(
                            subject="sales_rep",
                            action=PermissionAction.READ,
                            object_type="account",
                            scope="company",
                        ),
                    ),
                ),
            )
        )

        result = engine.authorize(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.READ,
            obj=self._account(owner="other_user"),
        )

        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(result.reasons, ("Permission matched.",))

    def test_owned_by_me_scope_allows_owner_update(self) -> None:
        engine = RBACEngine(
            roles=(
                Role(
                    id="sales_rep",
                    name="Sales Rep",
                    permissions=(
                        Permission(
                            subject="sales_rep",
                            action=PermissionAction.UPDATE,
                            object_type="account",
                            scope="owned_by_me",
                            fields=("status", "tags"),
                        ),
                    ),
                ),
            )
        )

        result = engine.authorize(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.UPDATE,
            obj=self._account(owner="ssabbani"),
            fields=("status",),
        )

        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_owned_by_me_scope_denies_non_owner_update(self) -> None:
        engine = RBACEngine(
            roles=(
                Role(
                    id="sales_rep",
                    name="Sales Rep",
                    permissions=(
                        Permission(
                            subject="sales_rep",
                            action=PermissionAction.UPDATE,
                            object_type="account",
                            scope="owned_by_me",
                        ),
                    ),
                ),
            )
        )

        result = engine.authorize(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.UPDATE,
            obj=self._account(owner="other_user"),
        )

        self.assertEqual(result.decision, PolicyDecision.DENY)
        self.assertIn("scope mismatch", result.reasons[0])

    def test_field_level_permission_denies_protected_field(self) -> None:
        engine = RBACEngine(
            roles=(
                Role(
                    id="sales_rep",
                    name="Sales Rep",
                    permissions=(
                        Permission(
                            subject="sales_rep",
                            action=PermissionAction.UPDATE,
                            object_type="account",
                            scope="owned_by_me",
                            fields=("status",),
                        ),
                    ),
                ),
            )
        )

        result = engine.authorize(
            user=User(id="usr_suman", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.UPDATE,
            obj=self._account(owner="ssabbani"),
            fields=("metadata",),
        )

        self.assertEqual(result.decision, PolicyDecision.DENY)
        self.assertEqual(result.reasons, ("Fields not permitted: metadata",))

    def test_admin_wildcard_permission_allows_any_object(self) -> None:
        engine = RBACEngine(
            roles=(
                Role(
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
                ),
            )
        )

        result = engine.authorize(
            user=User(id="usr_suman", username="ssabbani", roles=("founder",)),
            action=PermissionAction.DELETE,
            obj=self._account(owner="other_user"),
        )

        self.assertEqual(result.decision, PolicyDecision.ALLOW)

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
