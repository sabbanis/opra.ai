"""Mutation proposal service tests."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AccountStage,
    AuditEventWriter,
    CRMAccount,
    CustomerHealth,
    LocalObjectStore,
    MutationProposalError,
    MutationProposalService,
    MutationProposalStatus,
    Permission,
    PermissionAction,
    PolicyDecision,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    account_schema,
    approval_required,
    crm_lifecycle_validator,
)
from company_os_core.serialization import read_yaml, write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class MutationProposalTests(unittest.TestCase):
    def test_propose_valid_update_writes_proposal_without_mutating_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, stage=AccountStage.RENEWAL_DUE, version=2)

            written = self._service(root, store).propose(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                action=PermissionAction.UPDATE,
                before=before,
                after=after,
                schema=account_schema(),
                fields=("stage",),
                request_id="req_stage_update",
            )

            self.assertTrue(written.path.exists())
            self.assertEqual(written.proposal.id, "proposal_req_stage_update")
            self.assertEqual(written.proposal.status, MutationProposalStatus.PROPOSED)
            self.assertEqual(written.proposal.policy_decision, PolicyDecision.ALLOW)
            self.assertEqual(
                written.proposal.target_path,
                "modules/crm/objects/accounts/acct_acme.yaml",
            )
            self.assertEqual(written.proposal.after["stage"], "renewal_due")
            self.assertEqual(
                store.read_object("account", "acct_acme").data["stage"],
                "active_customer",
            )

    def test_proposal_records_required_approvers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(metadata={})
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, version=2, metadata={"segment": "strategic"})

            written = self._service(root, store).propose(
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
                action=PermissionAction.UPDATE,
                before=before,
                after=after,
                schema=account_schema(),
                fields=("metadata",),
                request_id="req_metadata",
            )

            self.assertEqual(written.proposal.policy_decision, PolicyDecision.REQUIRES_APPROVAL)
            self.assertEqual(written.proposal.required_approvers, ("sales_manager",))
            self.assertIn("approval", written.proposal.reasons[0])

    def test_invalid_stage_transition_does_not_write_proposal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, stage=AccountStage.LEAD, version=2)

            with self.assertRaises(MutationProposalError) as context:
                self._service(root, store).propose(
                    user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                    action=PermissionAction.UPDATE,
                    before=before,
                    after=after,
                    schema=account_schema(),
                    fields=("stage",),
                    request_id="req_invalid_stage",
                )

            self.assertIn("domain validation failed", str(context.exception))
            self.assertEqual(list((root / "platform/proposals/mutations").glob("*.yaml")), [])

    def test_policy_denied_update_does_not_write_proposal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, stage=AccountStage.RENEWAL_DUE, version=2)

            with self.assertRaises(MutationProposalError) as context:
                self._service(root, store).propose(
                    user=User(id="viewer", username="viewer", roles=()),
                    action=PermissionAction.UPDATE,
                    before=before,
                    after=after,
                    schema=account_schema(),
                    fields=("stage",),
                    request_id="req_denied",
                )

            self.assertIn("policy denied proposal", str(context.exception))
            self.assertEqual(list((root / "platform/proposals/mutations").glob("*.yaml")), [])

    def test_approve_required_proposal_records_approval_and_sets_approved(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(metadata={})
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, version=2, metadata={"segment": "strategic"})
            service = self._service(root, store)
            written = service.propose(
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
                action=PermissionAction.UPDATE,
                before=before,
                after=after,
                schema=account_schema(),
                fields=("metadata",),
                request_id="req_metadata",
            )

            approved = service.approve(
                path=written.path,
                user=User(id="manager", username="manager", roles=("sales_manager",)),
                reason="Approved for strategic account update.",
            )

            self.assertEqual(approved.proposal.status, MutationProposalStatus.APPROVED)
            self.assertEqual(len(approved.proposal.approvals), 1)
            self.assertEqual(approved.proposal.approvals[0].approver, "manager")
            self.assertIn("sales_manager", approved.proposal.approvals[0].subjects)
            self.assertEqual(service.remaining_approvers(approved.proposal), ())

            data = read_yaml(written.path)
            self.assertEqual(data["status"], "approved")
            self.assertEqual(data["approvals"][0]["decision"], "approved")

    def test_apply_approved_update_writes_source_and_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, stage=AccountStage.RENEWAL_DUE, version=2)
            service = self._service(root, store)
            written = service.propose(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                action=PermissionAction.UPDATE,
                before=before,
                after=after,
                schema=account_schema(),
                fields=("stage",),
                request_id="req_stage_update",
            )
            service.approve(
                path=written.path,
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )

            applied = service.apply(
                path=written.path,
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                schema=account_schema(),
                audit_writer=AuditEventWriter(root / "platform/audit/events"),
            )

            self.assertEqual(applied.proposal.status, MutationProposalStatus.APPLIED)
            self.assertEqual(
                store.read_object("account", "acct_acme").data["stage"],
                "renewal_due",
            )
            self.assertEqual(applied.audit_event.event.result.value, "completed")
            self.assertEqual(len(applied.audit_event.event.approval_chain), 1)
            self.assertEqual(
                read_yaml(written.path)["audit_event_id"],
                applied.audit_event.event.event_id,
            )

    def test_apply_rejects_stale_source_hash(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, stage=AccountStage.RENEWAL_DUE, version=2)
            service = self._service(root, store)
            written = service.propose(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                action=PermissionAction.UPDATE,
                before=before,
                after=after,
                schema=account_schema(),
                fields=("stage",),
                request_id="req_stage_update",
            )
            service.approve(
                path=written.path,
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )
            write_yaml(
                store.object_path("account", "acct_acme"),
                replace(original, version=3),
            )

            with self.assertRaises(MutationProposalError) as context:
                service.apply(
                    path=written.path,
                    user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                    schema=account_schema(),
                    audit_writer=AuditEventWriter(root / "platform/audit/events"),
                )

            self.assertIn("current object hash", str(context.exception))
            self.assertEqual(store.read_object("account", "acct_acme").data["version"], 3)

    def test_rejected_proposal_cannot_be_applied(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map=self._path_map())
            original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
            store.write_object(original, schema=account_schema())
            before = store.read_object("account", "acct_acme").data
            after = replace(original, stage=AccountStage.RENEWAL_DUE, version=2)
            service = self._service(root, store)
            written = service.propose(
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                action=PermissionAction.UPDATE,
                before=before,
                after=after,
                schema=account_schema(),
                fields=("stage",),
                request_id="req_stage_update",
            )
            service.reject(
                path=written.path,
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                reason="Needs more context.",
            )

            with self.assertRaises(MutationProposalError) as context:
                service.apply(
                    path=written.path,
                    user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                    schema=account_schema(),
                    audit_writer=AuditEventWriter(root / "platform/audit/events"),
                )

            self.assertIn("must be approved", str(context.exception))
            self.assertEqual(
                store.read_object("account", "acct_acme").data["stage"],
                "active_customer",
            )

    def _service(self, root: Path, store: LocalObjectStore) -> MutationProposalService:
        return MutationProposalService(
            repo_root=root,
            object_store=store,
            policy_engine=self._policy_engine(),
            domain_validators=(crm_lifecycle_validator,),
        )

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
        sales_rep = Role(
            id="sales_rep",
            name="Sales Rep",
            permissions=(
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.UPDATE,
                    object_type="account",
                    scope="owned_by_me",
                    fields=("metadata",),
                ),
            ),
        )
        return PolicyEngine(
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

    def _path_map(self):
        return {"account": "modules/crm/objects/accounts"}

    def _account(
        self,
        stage: AccountStage = AccountStage.ACTIVE_CUSTOMER,
        metadata=None,
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
            metadata=metadata or {},
        )


if __name__ == "__main__":
    unittest.main()
