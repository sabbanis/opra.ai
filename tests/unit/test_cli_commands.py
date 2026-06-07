"""CLI command tests."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AccountStage,
    ApprovalStatus,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    OpportunityStage,
)
from company_os_core.serialization import read_yaml, to_plain_data, write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class CliCommandTests(unittest.TestCase):
    def test_validate_passes_for_valid_object_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = self._write_valid_account(Path(temp_dir))

            result = subprocess.run(
                [sys.executable, "-m", "company_os_cli", "validate", "--file", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Validation passed:", result.stdout)

    def test_validate_fails_for_invalid_object_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = self._write_valid_account(Path(temp_dir))
            data = to_plain_data(self._valid_account())
            del data["owner"]
            write_yaml(path, data)

            result = subprocess.run(
                [sys.executable, "-m", "company_os_cli", "validate", "--file", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("- owner: field is required", result.stdout)

    def test_inspect_prints_json(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = self._write_valid_account(Path(temp_dir))

            result = subprocess.run(
                [sys.executable, "-m", "company_os_cli", "inspect", "--file", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn('"id": "acct_acme"', result.stdout)
            self.assertIn('"object_type": "account"', result.stdout)

    def test_policy_check_allows_founder(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = self._write_valid_account(Path(temp_dir))

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "policy-check",
                    "--file",
                    str(path),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "delete",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Decision: allow", result.stdout)

    def test_policy_check_requires_approval_for_demo_controlled_field(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = self._write_valid_account(Path(temp_dir))

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "policy-check",
                    "--file",
                    str(path),
                    "--user",
                    "ssabbani",
                    "--role",
                    "sales_rep",
                    "--action",
                    "update",
                    "--field",
                    "metadata",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Decision: requires_approval", result.stdout)
            self.assertIn("Required approvers:", result.stdout)
            self.assertIn("- sales_manager", result.stdout)

    def test_policy_check_denies_unpermitted_user(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = self._write_valid_account(Path(temp_dir))

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "policy-check",
                    "--file",
                    str(path),
                    "--user",
                    "viewer",
                    "--action",
                    "update",
                    "--field",
                    "status",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Decision: deny", result.stdout)

    def test_audit_record_writes_event_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            object_path = self._write_valid_account(root)
            event_dir = root / "platform/audit/events"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "audit-record",
                    "--event-dir",
                    str(event_dir),
                    "--actor",
                    "ssabbani",
                    "--action",
                    "create",
                    "--object-type",
                    "account",
                    "--object-id",
                    "acct_acme",
                    "--request-id",
                    "req_001",
                    "--after-file",
                    str(object_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Audit event written:", result.stdout)
            self.assertIn("Event id: evt_", result.stdout)
            self.assertEqual(len(list(event_dir.glob("evt_*.yaml"))), 1)

    def test_governed_write_creates_object_and_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = self._write_valid_account(root)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "governed-write",
                    "--file",
                    str(path),
                    "--repo-root",
                    str(root),
                    "--event-dir",
                    str(root / "platform/audit/events"),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "create",
                    "--request-id",
                    "req_001",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Decision: allow", result.stdout)
            self.assertIn("Stored object:", result.stdout)
            self.assertTrue((root / "modules/crm/objects/accounts/acct_acme.yaml").exists())
            self.assertEqual(len(list((root / "platform/audit/events").glob("evt_*.yaml"))), 1)

    def test_governed_write_blocks_invalid_crm_stage_update(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            write_yaml(stored_path, self._valid_account(stage=AccountStage.ACTIVE_CUSTOMER))
            write_yaml(input_path, self._valid_account(stage=AccountStage.LEAD))

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "governed-write",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--event-dir",
                    str(root / "platform/audit/events"),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "update",
                    "--field",
                    "stage",
                    "--request-id",
                    "req_invalid_stage",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Decision: deny", result.stdout)
            self.assertIn("invalid account stage transition", result.stdout)
            self.assertEqual(read_yaml(stored_path)["stage"], "active_customer")

    def test_propose_mutation_writes_review_artifact_without_changing_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            write_yaml(stored_path, self._valid_account(stage=AccountStage.ACTIVE_CUSTOMER))
            write_yaml(input_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "update",
                    "--field",
                    "stage",
                    "--request-id",
                    "req_stage_update",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            proposal_path = (
                root / "platform/proposals/mutations/proposal_req_stage_update.yaml"
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("Proposal written:", result.stdout)
            self.assertTrue(proposal_path.exists())
            self.assertEqual(read_yaml(stored_path)["stage"], "active_customer")
            self.assertEqual(read_yaml(proposal_path)["after"]["stage"], "renewal_due")

    def test_approve_and_apply_proposal_updates_source_and_audit(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = (
                root / "platform/proposals/mutations/proposal_req_stage_update.yaml"
            )
            event_dir = root / "platform/audit/events"
            write_yaml(stored_path, self._valid_account(stage=AccountStage.ACTIVE_CUSTOMER))
            write_yaml(input_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "update",
                    "--field",
                    "stage",
                    "--request-id",
                    "req_stage_update",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            approve = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "approve-proposal",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            apply = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "apply-proposal",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                    "--event-dir",
                    str(event_dir),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(approve.returncode, 0)
            self.assertEqual(apply.returncode, 0)
            self.assertIn("Proposal status: approved", approve.stdout)
            self.assertIn("Proposal status: applied", apply.stdout)
            self.assertEqual(read_yaml(stored_path)["stage"], "renewal_due")
            self.assertEqual(read_yaml(proposal_path)["status"], "applied")
            self.assertEqual(len(list(event_dir.glob("evt_*.yaml"))), 1)

    def test_publish_proposal_pr_writes_mock_preview(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = (
                root / "platform/proposals/mutations/proposal_req_stage_update.yaml"
            )
            preview_path = (
                root / "platform/integrations/github/pr_previews/proposal_req_stage_update.yaml"
            )
            write_yaml(stored_path, self._valid_account(stage=AccountStage.ACTIVE_CUSTOMER))
            write_yaml(input_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "update",
                    "--field",
                    "stage",
                    "--request-id",
                    "req_stage_update",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            publish = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "publish-proposal-pr",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                    "--repo-url",
                    "https://github.com/acme/opra.ai",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(publish.returncode, 0)
            self.assertIn("PR preview written:", publish.stdout)
            self.assertIn("https://github.com/acme/opra.ai/pull/1", publish.stdout)
            preview = read_yaml(preview_path)
            self.assertEqual(
                preview["branch_name"],
                "opra-ai/proposals/proposal_req_stage_update",
            )
            self.assertEqual(preview["pull_request"]["number"], 1)
            self.assertEqual(
                preview["files"][0]["path"],
                "modules/crm/objects/accounts/acct_acme.yaml",
            )

    def test_create_github_issue_writes_mock_preview(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview_path = root / "platform/integrations/github/issue_previews/issue_1.yaml"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "create-github-issue",
                    "--repo-root",
                    str(root),
                    "--repo-url",
                    "https://github.com/acme/opra.ai",
                    "--title",
                    "Customer-impacting defect",
                    "--body",
                    "Acme renewal blocker.",
                    "--label",
                    "defect",
                    "--assignee",
                    "ssabbani",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Issue preview written:", result.stdout)
            self.assertIn("Issue: #1", result.stdout)
            preview = read_yaml(preview_path)
            self.assertEqual(preview["title"], "Customer-impacting defect")
            self.assertEqual(preview["labels"], ["defect"])
            self.assertEqual(preview["assignees"], ["ssabbani"])
            self.assertEqual(preview["url"], "https://github.com/acme/opra.ai/issues/1")

    def test_update_github_issue_updates_mock_preview(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview_path = root / "platform/integrations/github/issue_previews/issue_1.yaml"
            create = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "create-github-issue",
                    "--repo-root",
                    str(root),
                    "--repo-url",
                    "https://github.com/acme/opra.ai",
                    "--title",
                    "Customer-impacting defect",
                    "--body",
                    "Acme renewal blocker.",
                    "--label",
                    "defect",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            update = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "update-github-issue",
                    "--repo-root",
                    str(root),
                    "--repo-url",
                    "https://github.com/acme/opra.ai",
                    "--number",
                    "1",
                    "--title",
                    "Customer-impacting defect: Acme",
                    "--state",
                    "closed",
                    "--label",
                    "triaged",
                    "--assignee",
                    "manager",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(create.returncode, 0)
            self.assertEqual(update.returncode, 0)
            self.assertIn("State: closed", update.stdout)
            preview = read_yaml(preview_path)
            self.assertEqual(preview["title"], "Customer-impacting defect: Acme")
            self.assertEqual(preview["state"], "closed")
            self.assertEqual(preview["labels"], ["defect", "triaged"])
            self.assertEqual(preview["assignees"], ["manager"])

    def test_validate_proposal_pr_passes_for_matching_target_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = (
                root / "platform/proposals/mutations/proposal_req_stage_update.yaml"
            )
            write_yaml(stored_path, self._valid_account(stage=AccountStage.ACTIVE_CUSTOMER))
            write_yaml(input_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "update",
                    "--field",
                    "stage",
                    "--request-id",
                    "req_stage_update",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            write_yaml(stored_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            validate = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "validate-proposal-pr",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(validate.returncode, 0)
            self.assertIn("Proposal PR validation passed:", validate.stdout)

    def test_validate_proposal_pr_requires_github_approval_evidence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = root / "platform/proposals/mutations/proposal_req_metadata.yaml"
            write_yaml(stored_path, self._valid_account())
            write_yaml(input_path, self._account_with_metadata({"segment": "strategic"}))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "sales_rep",
                    "--action",
                    "update",
                    "--field",
                    "metadata",
                    "--request-id",
                    "req_metadata",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            write_yaml(stored_path, self._account_with_metadata({"segment": "strategic"}))

            validate = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "validate-proposal-pr",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(validate.returncode, 1)
            self.assertIn("missing required approvals: sales_manager", validate.stdout)

    def test_validate_proposal_pr_accepts_mapped_github_approval(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = root / "platform/proposals/mutations/proposal_req_metadata.yaml"
            review_path = root / ".opra/github-pr-reviews.json"
            report_path = root / ".opra/proposal-check-report.md"
            self._write_approval_map(root)
            self._write_github_reviews(review_path)
            write_yaml(stored_path, self._valid_account())
            write_yaml(input_path, self._account_with_metadata({"segment": "strategic"}))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "sales_rep",
                    "--action",
                    "update",
                    "--field",
                    "metadata",
                    "--request-id",
                    "req_metadata",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            write_yaml(stored_path, self._account_with_metadata({"segment": "strategic"}))

            validate = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "validate-proposal-pr",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                    "--github-review-file",
                    str(review_path),
                    "--report-file",
                    str(report_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(validate.returncode, 0)
            self.assertIn("Proposal PR validation passed:", validate.stdout)
            self.assertIn("- Satisfied: sales_manager", validate.stdout)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("<!-- opra-ai-proposal-check -->", report)
            self.assertIn("- Status: `passed`", report)
            self.assertIn("- Satisfied approvers: `sales_manager`", report)

    def test_record_proposal_merge_marks_applied_and_writes_audit(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = (
                root / "platform/proposals/mutations/proposal_req_stage_update.yaml"
            )
            event_dir = root / "platform/audit/events"
            write_yaml(stored_path, self._valid_account(stage=AccountStage.ACTIVE_CUSTOMER))
            write_yaml(input_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "update",
                    "--field",
                    "stage",
                    "--request-id",
                    "req_stage_update",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            write_yaml(stored_path, self._valid_account(stage=AccountStage.RENEWAL_DUE))

            record = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "record-proposal-merge",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                    "--event-dir",
                    str(event_dir),
                    "--actor",
                    "github-actions",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(record.returncode, 0)
            self.assertIn("Proposal status: applied", record.stdout)
            self.assertEqual(read_yaml(proposal_path)["status"], "applied")
            self.assertEqual(read_yaml(proposal_path)["applied_by"], "github-actions")
            self.assertEqual(len(list(event_dir.glob("evt_*.yaml"))), 1)

    def test_record_proposal_merge_records_github_approval_evidence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stored_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            input_path = root / "input/acct_acme.yaml"
            proposal_path = root / "platform/proposals/mutations/proposal_req_metadata.yaml"
            review_path = root / ".opra/github-pr-reviews.json"
            event_dir = root / "platform/audit/events"
            self._write_approval_map(root)
            self._write_github_reviews(review_path)
            write_yaml(stored_path, self._valid_account())
            write_yaml(input_path, self._account_with_metadata({"segment": "strategic"}))

            propose = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "propose-mutation",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "sales_rep",
                    "--action",
                    "update",
                    "--field",
                    "metadata",
                    "--request-id",
                    "req_metadata",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            write_yaml(stored_path, self._account_with_metadata({"segment": "strategic"}))

            record = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "record-proposal-merge",
                    "--file",
                    str(proposal_path),
                    "--repo-root",
                    str(root),
                    "--event-dir",
                    str(event_dir),
                    "--actor",
                    "github-actions",
                    "--github-review-file",
                    str(review_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(propose.returncode, 0)
            self.assertEqual(record.returncode, 0)
            proposal = read_yaml(proposal_path)
            self.assertEqual(proposal["status"], "applied")
            self.assertEqual(proposal["approvals"][0]["approver"], "@sabbanis")
            audit_path = next(event_dir.glob("evt_*.yaml"))
            self.assertEqual(
                read_yaml(audit_path)["approval_chain"][0]["approver"],
                "@sabbanis",
            )

    def test_index_crm_writes_dashboard_read_model(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_yaml(
                root / "modules/crm/objects/accounts/acct_acme.yaml",
                self._valid_account(),
            )
            write_yaml(
                root / "modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml",
                self._valid_opportunity(),
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "index-crm",
                    "--repo-root",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            output_path = root / "platform/dashboards/read_models/crm_summary.json"
            self.assertEqual(result.returncode, 0)
            self.assertIn("CRM read model written:", result.stdout)
            self.assertIn("Accounts: 1", result.stdout)
            self.assertTrue(output_path.exists())
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["account_count"], 1)
            self.assertEqual(data["summary"]["weighted_pipeline_amount"], 325000)

    def test_crm_skill_runs_pipeline_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_yaml(
                root / "modules/crm/objects/accounts/acct_acme.yaml",
                self._valid_account(),
            )
            write_yaml(
                root / "modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml",
                self._valid_opportunity(),
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "crm-skill",
                    "--name",
                    "pipeline-summary",
                    "--repo-root",
                    str(root),
                    "--user",
                    "ssabbani",
                    "--role",
                    "sales_rep",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Skill: pipeline-summary", result.stdout)
            self.assertIn("Decision: allow", result.stdout)
            self.assertIn("500000 open pipeline", result.stdout)

    def _write_valid_account(self, root: Path) -> Path:
        path = root / "acct_acme.yaml"
        write_yaml(path, self._valid_account())
        return path

    def _valid_account(self, stage: AccountStage = AccountStage.ACTIVE_CUSTOMER) -> CRMAccount:
        return CRMAccount(
            id="acct_acme",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
            name="Acme Corp",
            stage=stage,
            industry="manufacturing",
            arr=250000,
            health=CustomerHealth.YELLOW,
            renewal_date="2026-09-30",
        )

    def _account_with_metadata(self, metadata) -> dict:
        data = to_plain_data(self._valid_account())
        data["version"] = 2
        data["metadata"] = metadata
        return data

    def _write_approval_map(self, root: Path) -> None:
        write_yaml(
            root / "platform/integrations/github/approval_owners.yaml",
            {
                "version": 1,
                "subjects": [
                    {
                        "subject": "sales_manager",
                        "owners": ["@sabbanis"],
                    }
                ],
            },
        )

    def _write_github_reviews(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "number": 42,
                    "url": "https://github.com/acme/opra.ai/pull/42",
                    "reviews": [
                        {
                            "author": {"login": "sabbanis"},
                            "state": "APPROVED",
                            "submittedAt": "2026-06-06T12:00:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _valid_opportunity(self) -> CRMOpportunity:
        return CRMOpportunity(
            id="opp_acme_renewal_2026",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
            account_id="acct_acme",
            stage=OpportunityStage.PROPOSAL,
            amount=500000,
            probability=0.65,
            close_date="2026-09-30",
            discount_requested=12,
            next_step="Send renewal proposal and technical validation plan",
            approval_status=ApprovalStatus.PENDING_FINANCE,
        )


if __name__ == "__main__":
    unittest.main()
