"""CRM read-model indexing tests."""

from datetime import datetime, timezone
import json
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
    ReadModelBuildError,
    build_crm_read_model,
    write_crm_read_model,
)
from company_os_core.serialization import to_plain_data, write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class CRMReadModelTests(unittest.TestCase):
    def test_build_crm_read_model_summarizes_accounts_and_pipeline(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_account(root, self._account())
            self._write_opportunity(root, self._opportunity())
            self._write_opportunity(
                root,
                self._opportunity(
                    opportunity_id="opp_closed_lost",
                    stage=OpportunityStage.CLOSED_LOST,
                    amount=100000,
                    probability=0.1,
                ),
            )

            read_model = build_crm_read_model(root, generated_at=TIMESTAMP)

            self.assertEqual(read_model.summary.account_count, 1)
            self.assertEqual(read_model.summary.opportunity_count, 2)
            self.assertEqual(read_model.summary.total_arr, 250000)
            self.assertEqual(read_model.summary.open_pipeline_amount, 500000)
            self.assertEqual(read_model.summary.weighted_pipeline_amount, 325000)
            self.assertEqual(read_model.summary.renewal_account_count, 0)
            self.assertEqual(read_model.summary.at_risk_account_count, 1)

            account = read_model.accounts[0]
            self.assertEqual(account.id, "acct_acme")
            self.assertEqual(account.open_opportunity_count, 1)
            self.assertEqual(account.next_close_date, "2026-09-30")

            opportunity = read_model.opportunities[0]
            self.assertEqual(opportunity.account_name, "Acme Corp")
            self.assertEqual(opportunity.weighted_amount, 325000)

    def test_write_crm_read_model_writes_json_artifact(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_account(root, self._account(stage=AccountStage.RENEWAL_DUE))
            self._write_opportunity(root, self._opportunity())

            written = write_crm_read_model(root, generated_at=TIMESTAMP)

            self.assertTrue(written.path.exists())
            data = json.loads(written.path.read_text(encoding="utf-8"))
            self.assertEqual(data["generated_at"], "2026-06-06T10:00:00Z")
            self.assertEqual(data["summary"]["renewal_account_count"], 1)
            self.assertEqual(data["accounts"][0]["name"], "Acme Corp")

    def test_build_crm_read_model_rejects_invalid_source_object(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = to_plain_data(self._account())
            del data["name"]
            write_yaml(root / "modules/crm/objects/accounts/acct_acme.yaml", data)

            with self.assertRaises(ReadModelBuildError) as context:
                build_crm_read_model(root, generated_at=TIMESTAMP)

            self.assertIn("name: field is required", str(context.exception))

    def _write_account(self, root: Path, account: CRMAccount) -> None:
        write_yaml(root / f"modules/crm/objects/accounts/{account.id}.yaml", account)

    def _write_opportunity(self, root: Path, opportunity: CRMOpportunity) -> None:
        write_yaml(
            root / f"modules/crm/objects/opportunities/{opportunity.id}.yaml",
            opportunity,
        )

    def _account(
        self,
        stage: AccountStage = AccountStage.ACTIVE_CUSTOMER,
    ) -> CRMAccount:
        return CRMAccount(
            id="acct_acme",
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            name="Acme Corp",
            stage=stage,
            industry="manufacturing",
            arr=250000,
            health=CustomerHealth.YELLOW,
            renewal_date="2026-09-30",
        )

    def _opportunity(
        self,
        opportunity_id: str = "opp_acme_renewal_2026",
        stage: OpportunityStage = OpportunityStage.PROPOSAL,
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
            account_id="acct_acme",
            stage=stage,
            amount=amount,
            probability=probability,
            close_date="2026-09-30",
            discount_requested=12,
            next_step="Send renewal proposal and technical validation plan",
            approval_status=ApprovalStatus.PENDING_FINANCE,
        )


if __name__ == "__main__":
    unittest.main()
