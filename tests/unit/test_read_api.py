"""Local read API tests."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    APIResponse,
    AccountStage,
    ApprovalStatus,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    LocalReadAPI,
    OpportunityStage,
    Permission,
    PermissionAction,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
)
from company_os_core.serialization import write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class LocalReadAPITests(unittest.TestCase):
    def test_root_returns_api_index(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/",
            query={},
            user=User(id="anonymous", username="anonymous"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["name"], "opra.ai API")
        self.assertIn("/crm/summary", response.body["endpoints"])

    def test_health_returns_ok_without_crm_data(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/health",
            query={},
            user=User(id="anonymous", username="anonymous"),
        )

        self.assertEqual(response, APIResponse(status_code=200, body={"status": "ok"}))

    def test_crm_summary_returns_authorized_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/summary",
                query={},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body["summary"]["account_count"], 1)
            self.assertEqual(response.body["summary"]["weighted_pipeline_amount"], 325000)

    def test_crm_accounts_denies_user_without_read_permission(self) -> None:
        with TemporaryDirectory() as temp_dir:
            api = LocalReadAPI(repo_root=Path(temp_dir), policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/accounts",
                query={},
                user=User(id="viewer", username="viewer", roles=()),
            )

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.body["object_type"], "account")

    def test_crm_opportunities_filters_by_account_and_limit(self) -> None:
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
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/opportunities",
                query={"account_id": "acct_other", "limit": "1"},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 200)
            opportunities = response.body["opportunities"]
            self.assertEqual(len(opportunities), 1)
            self.assertEqual(opportunities[0]["id"], "opp_other")

    def test_crm_skill_endpoint_returns_skill_result(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/skills/pipeline-summary",
                query={"limit": "1"},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body["decision"], "allow")
            self.assertIn("500000 open pipeline", response.body["summary"])

    def test_unknown_crm_skill_returns_not_found(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/crm/skills/missing",
            query={},
            user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
        )

        self.assertEqual(response.status_code, 404)

    def test_unknown_route_returns_not_found(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/missing",
            query={},
            user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
        )

        self.assertEqual(response.status_code, 404)

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

    def _write_seed(self, root: Path) -> None:
        self._write_account(root, self._account())
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
    ) -> CRMAccount:
        return CRMAccount(
            id=account_id,
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            name=name,
            stage=AccountStage.ACTIVE_CUSTOMER,
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
