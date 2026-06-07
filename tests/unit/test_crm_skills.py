"""CRM Skill handler tests."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AccountStage,
    ApprovalStatus,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    OpportunityStage,
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    crm_skill_descriptors,
    run_crm_skill,
)
from company_os_core.serialization import write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class CRMSkillTests(unittest.TestCase):
    def test_skill_descriptors_include_crm_read_handlers(self) -> None:
        names = tuple(descriptor.name for descriptor in crm_skill_descriptors())

        self.assertIn("pipeline-summary", names)
        self.assertIn("renewal-health", names)
        self.assertIn("opportunity-view", names)

    def test_pipeline_summary_returns_governed_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)

            result = run_crm_skill(
                name="pipeline-summary",
                repo_root=root,
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
                policy_engine=self._policy_engine(),
            )

            self.assertTrue(result.allowed)
            self.assertEqual(result.decision, PolicyDecision.ALLOW)
            self.assertIn("500000 open pipeline", result.summary)
            self.assertEqual(result.data["summary"]["weighted_pipeline_amount"], 325000)
            self.assertEqual(result.data["top_opportunities"][0]["id"], "opp_acme_renewal_2026")

    def test_renewal_health_returns_at_risk_accounts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root, account_stage=AccountStage.RENEWAL_DUE)

            result = run_crm_skill(
                name="renewal-health",
                repo_root=root,
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
                policy_engine=self._policy_engine(),
            )

            self.assertTrue(result.allowed)
            self.assertEqual(result.summary, "1 renewal or at-risk accounts need attention.")
            self.assertEqual(result.data["accounts"][0]["id"], "acct_acme")

    def test_opportunity_view_filters_by_account(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            self._write_account(root, self._account(account_id="acct_other", name="Other Corp"))
            self._write_opportunity(
                root,
                self._opportunity(
                    opportunity_id="opp_other",
                    account_id="acct_other",
                    amount=900000,
                    probability=0.2,
                ),
            )

            result = run_crm_skill(
                name="opportunity-view",
                repo_root=root,
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
                policy_engine=self._policy_engine(),
                inputs={"account_id": "acct_acme", "limit": 10},
            )

            self.assertTrue(result.allowed)
            self.assertEqual(result.data["account_id"], "acct_acme")
            self.assertEqual(len(result.data["opportunities"]), 1)
            self.assertEqual(result.data["opportunities"][0]["account_id"], "acct_acme")

    def test_skill_denies_user_without_read_permission(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)

            result = run_crm_skill(
                name="pipeline-summary",
                repo_root=root,
                user=User(id="viewer", username="viewer", roles=()),
                policy_engine=self._policy_engine(),
            )

            self.assertFalse(result.allowed)
            self.assertEqual(result.decision, PolicyDecision.DENY)
            self.assertIn("account: No matching permission.", result.reasons)

    def _policy_engine(self) -> PolicyEngine:
        sales_rep = Role(
            id="sales_rep",
            name="Sales Rep",
            permissions=(
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.READ,
                    object_type="account",
                    scope="company",
                ),
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.READ,
                    object_type="opportunity",
                    scope="company",
                ),
            ),
        )
        return PolicyEngine(rbac=RBACEngine(roles=(sales_rep,)))

    def _write_seed(
        self,
        root: Path,
        account_stage: AccountStage = AccountStage.ACTIVE_CUSTOMER,
    ) -> None:
        self._write_account(root, self._account(stage=account_stage))
        self._write_opportunity(root, self._opportunity())

    def _write_account(self, root: Path, account: CRMAccount) -> None:
        write_yaml(root / f"modules/crm/objects/accounts/{account.id}.yaml", account)

    def _write_opportunity(self, root: Path, opportunity: CRMOpportunity) -> None:
        write_yaml(
            root / f"modules/crm/objects/opportunities/{opportunity.id}.yaml",
            opportunity,
        )

    def _account(
        self,
        account_id: str = "acct_acme",
        name: str = "Acme Corp",
        stage: AccountStage = AccountStage.ACTIVE_CUSTOMER,
    ) -> CRMAccount:
        return CRMAccount(
            id=account_id,
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            name=name,
            stage=stage,
            industry="manufacturing",
            arr=250000,
            health=CustomerHealth.YELLOW,
            renewal_date="2026-09-30",
        )

    def _opportunity(
        self,
        opportunity_id: str = "opp_acme_renewal_2026",
        account_id: str = "acct_acme",
        amount: int = 500000,
        probability: float = 0.65,
    ) -> CRMOpportunity:
        return CRMOpportunity(
            id=opportunity_id,
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            account_id=account_id,
            stage=OpportunityStage.PROPOSAL,
            amount=amount,
            probability=probability,
            close_date="2026-09-30",
            discount_requested=12,
            next_step="Send renewal proposal and technical validation plan",
            approval_status=ApprovalStatus.PENDING_FINANCE,
        )


if __name__ == "__main__":
    unittest.main()
