"""CRM module model and schema tests."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AccountStage,
    ApprovalStatus,
    AuditEventWriter,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    GovernedMutationService,
    LocalObjectStore,
    OpportunityStage,
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    account_schema,
    crm_lifecycle_validator,
    opportunity_schema,
)
from company_os_core.serialization import read_yaml, to_plain_data
from company_os_core.schema import validate_object


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class CRMModuleTests(unittest.TestCase):
    def test_account_schema_accepts_valid_account(self) -> None:
        result = validate_object(to_plain_data(self._account()), account_schema())

        self.assertTrue(result.valid)

    def test_account_schema_rejects_invalid_stage(self) -> None:
        data = to_plain_data(self._account())
        data["stage"] = "invalid_stage"

        result = validate_object(data, account_schema())

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "stage")

    def test_opportunity_schema_accepts_valid_opportunity(self) -> None:
        result = validate_object(to_plain_data(self._opportunity()), opportunity_schema())

        self.assertTrue(result.valid)

    def test_opportunity_schema_rejects_probability_above_one(self) -> None:
        data = to_plain_data(self._opportunity())
        data["probability"] = 1.2

        result = validate_object(data, opportunity_schema())

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "probability")
        self.assertIn("less than or equal to 1", result.issues[0].message)

    def test_account_lifecycle_allows_valid_stage_transition(self) -> None:
        before = to_plain_data(self._account(stage=AccountStage.ACTIVE_CUSTOMER))
        after = to_plain_data(self._account(stage=AccountStage.RENEWAL_DUE))

        result = crm_lifecycle_validator(before, after, PermissionAction.UPDATE)

        self.assertTrue(result.valid)

    def test_account_lifecycle_rejects_backward_stage_transition(self) -> None:
        before = to_plain_data(self._account(stage=AccountStage.ACTIVE_CUSTOMER))
        after = to_plain_data(self._account(stage=AccountStage.LEAD))

        result = crm_lifecycle_validator(before, after, PermissionAction.UPDATE)

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "stage")
        self.assertIn("active_customer -> lead", result.issues[0].message)

    def test_opportunity_lifecycle_allows_valid_stage_transition(self) -> None:
        before = to_plain_data(self._opportunity(stage=OpportunityStage.PROPOSAL))
        after = to_plain_data(self._opportunity(stage=OpportunityStage.NEGOTIATION))

        result = crm_lifecycle_validator(before, after, PermissionAction.UPDATE)

        self.assertTrue(result.valid)

    def test_opportunity_lifecycle_rejects_jump_to_closed_won(self) -> None:
        before = to_plain_data(self._opportunity(stage=OpportunityStage.PROPOSAL))
        after = to_plain_data(self._opportunity(stage=OpportunityStage.CLOSED_WON))

        result = crm_lifecycle_validator(before, after, PermissionAction.UPDATE)

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "stage")
        self.assertIn("proposal -> closed_won", result.issues[0].message)

    def test_seed_account_and_opportunity_validate(self) -> None:
        account = read_yaml(Path("modules/crm/objects/accounts/acct_acme.yaml"))
        opportunity = read_yaml(
            Path("modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml")
        )

        self.assertTrue(validate_object(account, account_schema()).valid)
        self.assertTrue(validate_object(opportunity, opportunity_schema()).valid)

    def test_governed_write_stores_crm_account_with_schema(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = GovernedMutationService(
                object_store=LocalObjectStore(
                    root,
                    path_map={"account": "modules/crm/objects/accounts"},
                ),
                policy_engine=self._policy_engine(),
                audit_writer=AuditEventWriter(root / "platform/audit/events"),
                domain_validators=(crm_lifecycle_validator,),
            )

            result = service.create_object(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                obj=self._account(),
                schema=account_schema(),
                request_id="req_crm_account",
            )

            self.assertEqual(result.policy_result.decision, PolicyDecision.ALLOW)
            self.assertTrue(result.committed)
            self.assertTrue((root / "modules/crm/objects/accounts/acct_acme.yaml").exists())

    def test_governed_update_blocks_invalid_crm_stage_transition(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map={"account": "modules/crm/objects/accounts"})
            service = GovernedMutationService(
                object_store=store,
                policy_engine=self._policy_engine(),
                audit_writer=AuditEventWriter(root / "platform/audit/events"),
                domain_validators=(crm_lifecycle_validator,),
            )
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data

            result = service.update_object(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                before=before,
                after=replace(original, stage=AccountStage.LEAD, version=2),
                schema=account_schema(),
                fields=("stage",),
                request_id="req_invalid_stage",
            )

            self.assertEqual(result.policy_result.decision, PolicyDecision.DENY)
            self.assertFalse(result.validation_result.valid)
            self.assertFalse(result.committed)
            self.assertEqual(result.audit_event.event.result.value, "failed")
            stored_stage = store.read_object("account", "acct_acme").data["stage"]
            self.assertEqual(stored_stage, "active_customer")

    def _policy_engine(self) -> PolicyEngine:
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
        return PolicyEngine(rbac=RBACEngine(roles=(founder,)))

    def _account(self, stage: AccountStage = AccountStage.ACTIVE_CUSTOMER) -> CRMAccount:
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
            tags=("design_partner", "strategic"),
        )

    def _opportunity(self, stage: OpportunityStage = OpportunityStage.PROPOSAL) -> CRMOpportunity:
        return CRMOpportunity(
            id="opp_acme_renewal_2026",
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            account_id="acct_acme",
            stage=stage,
            amount=500000,
            probability=0.65,
            close_date="2026-09-30",
            discount_requested=12,
            next_step="Send renewal proposal and technical validation plan",
            approval_status=ApprovalStatus.PENDING_FINANCE,
            tags=("renewal", "design_partner"),
        )


if __name__ == "__main__":
    unittest.main()
