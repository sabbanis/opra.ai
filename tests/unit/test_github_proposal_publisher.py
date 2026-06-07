"""GitHub proposal publisher tests."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    AccountStage,
    AuditEventWriter,
    CommandResult,
    CRMAccount,
    CustomerHealth,
    GitHubApprovalMap,
    GitHubApprovalOwner,
    GitHubCLIAdapter,
    GitHubFileChange,
    GitHubProposalPublisher,
    GitHubPublishError,
    LocalObjectStore,
    MockGitHubAdapter,
    MutationProposalService,
    MutationProposalStatus,
    Permission,
    PermissionAction,
    PolicyEngine,
    PROPOSAL_PR_REPORT_MARKER,
    ProposalMergeRecorder,
    ProposalPRValidator,
    RBACEngine,
    Role,
    User,
    account_schema,
    approval_required,
    crm_lifecycle_validator,
    github_approval_evidence_from_pull_request_data,
    issue_from_data,
    render_proposal_pr_validation_report,
)
from company_os_core.serialization import read_yaml, write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class GitHubProposalPublisherTests(unittest.TestCase):
    def test_publish_proposal_builds_branch_commit_and_pull_request(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal(root)
            adapter = MockGitHubAdapter(repo_url="https://github.com/acme/opra.ai")

            published = GitHubProposalPublisher(adapter=adapter, repo_root=root).publish(
                proposal=proposal,
                proposal_path=proposal_path,
                base_branch="main",
            )

            self.assertEqual(published.proposal_id, "proposal_req_stage_update")
            self.assertEqual(
                published.branch_name,
                "opra-ai/proposals/proposal_req_stage_update",
            )
            self.assertEqual(published.commit.branch, published.branch_name)
            self.assertEqual(published.commit.file_paths[0], proposal.target_path)
            self.assertEqual(
                published.commit.file_paths[1],
                "platform/proposals/mutations/proposal_req_stage_update.yaml",
            )
            self.assertEqual(published.pull_request.number, 1)
            self.assertEqual(
                published.pull_request.url,
                "https://github.com/acme/opra.ai/pull/1",
            )
            self.assertIn("proposal_req_stage_update", published.pull_request.body)
            self.assertIn("Before hash", published.pull_request.body)

    def test_rejected_proposal_cannot_be_published(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal(root)
            service = self._service(root)
            rejected = service.reject(
                path=proposal_path,
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
                reason="Not ready.",
            ).proposal

            with self.assertRaises(GitHubPublishError) as context:
                GitHubProposalPublisher(
                    adapter=MockGitHubAdapter(),
                    repo_root=root,
                ).publish(proposal=rejected, proposal_path=proposal_path)

            self.assertIn("cannot be published", str(context.exception))
            self.assertEqual(proposal.status.value, "proposed")

    def test_mock_adapter_returns_existing_pr_for_same_branch(self) -> None:
        adapter = MockGitHubAdapter(repo_url="https://github.com/acme/opra.ai")
        adapter.create_branch("opra-ai/proposals/proposal_a", "main")

        first = adapter.open_pull_request(
            branch_name="opra-ai/proposals/proposal_a",
            base_branch="main",
            title="First",
            body="Body",
        )
        second = adapter.open_pull_request(
            branch_name="opra-ai/proposals/proposal_a",
            base_branch="main",
            title="Second",
            body="Body",
        )

        self.assertEqual(first, second)
        self.assertEqual(len(adapter.pull_requests), 1)

    def test_mock_adapter_creates_and_updates_issue(self) -> None:
        adapter = MockGitHubAdapter(repo_url="https://github.com/acme/opra.ai")

        created = adapter.create_issue(
            title="Customer-impacting defect",
            body="Acme renewal blocker.",
            labels=("defect", "customer-impact"),
            assignees=("ssabbani",),
        )
        updated = adapter.update_issue(
            number=created.number,
            title="Customer-impacting defect: Acme",
            state="closed",
            labels=("triaged",),
        )

        self.assertEqual(created.number, 1)
        self.assertEqual(created.url, "https://github.com/acme/opra.ai/issues/1")
        self.assertEqual(updated.title, "Customer-impacting defect: Acme")
        self.assertEqual(updated.state, "closed")
        self.assertEqual(updated.labels, ("defect", "customer-impact", "triaged"))
        self.assertEqual(updated.assignees, ("ssabbani",))

    def test_issue_from_data_parses_serialized_issue_preview(self) -> None:
        issue = issue_from_data(
            {
                "number": 7,
                "title": "Sync issue",
                "body": "Body",
                "state": "OPEN",
                "labels": ["integration"],
                "assignees": ["ssabbani"],
                "url": "https://github.com/acme/opra.ai/issues/7",
            }
        )

        self.assertEqual(issue.number, 7)
        self.assertEqual(issue.state, "open")
        self.assertEqual(issue.labels, ("integration",))
        self.assertEqual(issue.assignees, ("ssabbani",))

    def test_cli_adapter_runs_git_and_gh_commands(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = RecordingRunner()
            adapter = GitHubCLIAdapter(repo_root=root, runner=runner)
            files = (
                GitHubFileChange(
                    path="modules/crm/objects/accounts/acct_acme.yaml",
                    content="id: acct_acme\n",
                ),
            )

            adapter.create_branch("opra-ai/proposals/proposal_a", "main")
            commit = adapter.commit_files(
                branch_name="opra-ai/proposals/proposal_a",
                message="Update account",
                files=files,
            )
            pull_request = adapter.open_pull_request(
                branch_name="opra-ai/proposals/proposal_a",
                base_branch="main",
                title="Update account",
                body="Body",
            )

            self.assertEqual(commit.branch, "opra-ai/proposals/proposal_a")
            self.assertEqual(
                (root / "modules/crm/objects/accounts/acct_acme.yaml").read_text(
                    encoding="utf-8"
                ),
                "id: acct_acme\n",
            )
            self.assertEqual(pull_request.number, 42)
            self.assertEqual(
                pull_request.url,
                "https://github.com/acme/opra.ai/pull/42",
            )
            commands = tuple(call.args for call in runner.calls)
            self.assertIn(("git", "fetch", "origin", "main"), commands)
            self.assertIn(
                (
                    "git",
                    "switch",
                    "-C",
                    "opra-ai/proposals/proposal_a",
                    "origin/main",
                ),
                commands,
            )
            self.assertIn(("git", "commit", "-m", "Update account"), commands)
            self.assertIn(
                ("git", "push", "-u", "origin", "opra-ai/proposals/proposal_a"),
                commands,
            )
            self.assertTrue(
                any(command[:3] == ("gh", "pr", "create") for command in commands)
            )

    def test_cli_adapter_runs_gh_issue_create_and_update_commands(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runner = RecordingRunner()
            adapter = GitHubCLIAdapter(repo_root=root, runner=runner)

            created = adapter.create_issue(
                title="Customer-impacting defect",
                body="Acme renewal blocker.",
                labels=("defect",),
                assignees=("ssabbani",),
            )
            updated = adapter.update_issue(
                number=created.number,
                title="Customer-impacting defect: Acme",
                body="Triaged.",
                state="closed",
                labels=("triaged",),
                assignees=("manager",),
            )

            self.assertEqual(created.number, 99)
            self.assertEqual(updated.state, "closed")
            commands = tuple(call.args for call in runner.calls)
            self.assertIn(
                (
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    "Customer-impacting defect",
                    "--body",
                    "Acme renewal blocker.",
                    "--label",
                    "defect",
                    "--assignee",
                    "ssabbani",
                ),
                commands,
            )
            self.assertIn(
                (
                    "gh",
                    "issue",
                    "edit",
                    "99",
                    "--title",
                    "Customer-impacting defect: Acme",
                    "--body",
                    "Triaged.",
                    "--add-label",
                    "triaged",
                    "--add-assignee",
                    "manager",
                ),
                commands,
            )
            self.assertIn(("gh", "issue", "close", "99"), commands)

    def test_cli_adapter_blocks_paths_outside_repo(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = GitHubCLIAdapter(repo_root=Path(temp_dir), runner=RecordingRunner())

            with self.assertRaises(GitHubPublishError) as context:
                adapter.commit_files(
                    branch_name="opra-ai/proposals/proposal_a",
                    message="Bad path",
                    files=(GitHubFileChange(path="../outside.yaml", content="bad"),),
                )

            self.assertIn("escapes repository root", str(context.exception))

    def test_proposal_pr_validator_accepts_matching_target_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal(root)
            write_yaml(root / proposal.target_path, proposal.after)

            result = ProposalPRValidator(repo_root=root).validate(
                proposal=proposal,
                proposal_path=proposal_path,
            )

            self.assertTrue(result.valid)
            self.assertEqual(result.issues, ())

    def test_proposal_pr_validator_rejects_target_hash_mismatch(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal(root)
            write_yaml(root / proposal.target_path, self._account(AccountStage.ACTIVE_CUSTOMER))

            result = ProposalPRValidator(repo_root=root).validate(
                proposal=proposal,
                proposal_path=proposal_path,
            )

            self.assertFalse(result.valid)
            self.assertIn(
                "target file content does not match",
                result.issues[0].message,
            )

    def test_proposal_pr_validator_rejects_missing_required_github_approval(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal_requiring_sales_manager(root)
            write_yaml(root / proposal.target_path, proposal.after)

            result = ProposalPRValidator(repo_root=root).validate(
                proposal=proposal,
                proposal_path=proposal_path,
            )

            self.assertFalse(result.valid)
            self.assertEqual(result.issues[-1].field, "approvals")
            self.assertIn("sales_manager", result.issues[-1].message)

    def test_github_review_evidence_satisfies_required_approver(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal_requiring_sales_manager(root)
            write_yaml(root / proposal.target_path, proposal.after)
            evidence = github_approval_evidence_from_pull_request_data(
                proposal=proposal,
                data=self._github_review_data(),
                approval_map=self._approval_map(),
            )

            result = ProposalPRValidator(repo_root=root).validate(
                proposal=proposal,
                proposal_path=proposal_path,
                approval_evidence=evidence,
            )

            self.assertTrue(result.valid)
            self.assertEqual(evidence.satisfied_approvers, ("sales_manager",))
            self.assertEqual(evidence.missing_approvers, ())
            self.assertEqual(evidence.approvals[0].approver, "@sabbanis")
            self.assertIn("sales_manager", evidence.approvals[0].subjects)

    def test_github_review_evidence_uses_latest_reviewer_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal_requiring_sales_manager(root)
            write_yaml(root / proposal.target_path, proposal.after)
            evidence = github_approval_evidence_from_pull_request_data(
                proposal=proposal,
                data={
                    "number": 42,
                    "url": "https://github.com/acme/opra.ai/pull/42",
                    "reviews": [
                        {
                            "author": {"login": "sabbanis"},
                            "state": "APPROVED",
                            "submittedAt": "2026-06-06T12:00:00Z",
                        },
                        {
                            "author": {"login": "sabbanis"},
                            "state": "CHANGES_REQUESTED",
                            "submittedAt": "2026-06-06T12:05:00Z",
                        },
                    ],
                },
                approval_map=self._approval_map(),
            )

            result = ProposalPRValidator(repo_root=root).validate(
                proposal=proposal,
                proposal_path=proposal_path,
                approval_evidence=evidence,
            )

            self.assertFalse(result.valid)
            self.assertEqual(evidence.satisfied_approvers, ())
            self.assertEqual(evidence.missing_approvers, ("sales_manager",))

    def test_validation_report_includes_status_issues_and_approval_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal_requiring_sales_manager(root)
            write_yaml(root / proposal.target_path, proposal.after)
            result = ProposalPRValidator(repo_root=root).validate(
                proposal=proposal,
                proposal_path=proposal_path,
            )

            report = render_proposal_pr_validation_report(
                proposal=proposal,
                result=result,
                proposal_path=proposal_path,
            )

            self.assertIn(PROPOSAL_PR_REPORT_MARKER, report)
            self.assertIn("- Status: `failed`", report)
            self.assertIn("- Missing approvers: `sales_manager`", report)
            self.assertIn("`approvals`: missing required approvals: sales_manager", report)
            self.assertIn("proposal_req_metadata", report)

    def test_merge_recorder_marks_proposal_applied_and_writes_audit(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal(root)
            event_dir = root / "platform/audit/events"
            write_yaml(root / proposal.target_path, proposal.after)

            recorded = ProposalMergeRecorder(
                repo_root=root,
                audit_writer=AuditEventWriter(event_dir),
            ).record(
                proposal=proposal,
                proposal_path=proposal_path,
                actor="github-actions",
            )

            self.assertEqual(recorded.proposal.status, MutationProposalStatus.APPLIED)
            self.assertEqual(recorded.proposal.applied_by, "github-actions")
            self.assertEqual(
                recorded.proposal.audit_event_id,
                recorded.audit_event.event.event_id,
            )
            self.assertEqual(read_yaml(proposal_path)["status"], "applied")
            self.assertEqual(read_yaml(root / proposal.target_path)["stage"], "renewal_due")
            audit = read_yaml(recorded.audit_event.path)
            self.assertEqual(audit["actor"], "github-actions")
            self.assertEqual(audit["action"], "update")
            self.assertEqual(audit["source"]["interface"], "github")
            self.assertEqual(audit["after_hash"], proposal.after_hash)

    def test_merge_recorder_records_github_approval_evidence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal_requiring_sales_manager(root)
            event_dir = root / "platform/audit/events"
            write_yaml(root / proposal.target_path, proposal.after)
            evidence = github_approval_evidence_from_pull_request_data(
                proposal=proposal,
                data=self._github_review_data(),
                approval_map=self._approval_map(),
            )

            recorded = ProposalMergeRecorder(
                repo_root=root,
                audit_writer=AuditEventWriter(event_dir),
            ).record(
                proposal=proposal,
                proposal_path=proposal_path,
                actor="github-actions",
                approval_evidence=evidence,
            )

            self.assertEqual(recorded.proposal.status, MutationProposalStatus.APPLIED)
            self.assertEqual(len(recorded.proposal.approvals), 1)
            self.assertEqual(recorded.proposal.approvals[0].approver, "@sabbanis")
            self.assertEqual(read_yaml(proposal_path)["approvals"][0]["approver"], "@sabbanis")
            audit = read_yaml(recorded.audit_event.path)
            self.assertEqual(audit["approval_chain"][0]["approver"], "@sabbanis")

    def test_merge_recorder_rejects_mismatched_target_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path, proposal = self._proposal(root)
            event_dir = root / "platform/audit/events"
            write_yaml(root / proposal.target_path, self._account(AccountStage.ACTIVE_CUSTOMER))

            with self.assertRaises(GitHubPublishError) as context:
                ProposalMergeRecorder(
                    repo_root=root,
                    audit_writer=AuditEventWriter(event_dir),
                ).record(
                    proposal=proposal,
                    proposal_path=proposal_path,
                    actor="github-actions",
                )

            self.assertIn("proposal merge validation failed", str(context.exception))
            self.assertEqual(read_yaml(proposal_path)["status"], "proposed")
            self.assertEqual(tuple(event_dir.glob("evt_*.yaml")), ())

    def _proposal(self, root: Path):
        store = LocalObjectStore(root, path_map={"account": "modules/crm/objects/accounts"})
        original = self._account(stage=AccountStage.ACTIVE_CUSTOMER)
        store.write_object(original, schema=account_schema())
        before = store.read_object("account", "acct_acme").data
        after = replace(original, stage=AccountStage.RENEWAL_DUE, version=2)
        service = self._service(root)
        written = service.propose(
            user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            action=PermissionAction.UPDATE,
            before=before,
            after=after,
            schema=account_schema(),
            fields=("stage",),
            request_id="req_stage_update",
        )
        return written.path, written.proposal

    def _proposal_requiring_sales_manager(self, root: Path):
        store = LocalObjectStore(root, path_map={"account": "modules/crm/objects/accounts"})
        original = self._account(AccountStage.ACTIVE_CUSTOMER, metadata={})
        store.write_object(original, schema=account_schema())
        before = store.read_object("account", "acct_acme").data
        after = replace(original, version=2, metadata={"segment": "strategic"})
        service = MutationProposalService(
            repo_root=root,
            object_store=store,
            policy_engine=self._approval_policy_engine(),
            domain_validators=(crm_lifecycle_validator,),
        )
        written = service.propose(
            user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            action=PermissionAction.UPDATE,
            before=before,
            after=after,
            schema=account_schema(),
            fields=("metadata",),
            request_id="req_metadata",
        )
        return written.path, written.proposal

    def _service(self, root: Path) -> MutationProposalService:
        return MutationProposalService(
            repo_root=root,
            object_store=LocalObjectStore(
                root,
                path_map={"account": "modules/crm/objects/accounts"},
            ),
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
        return PolicyEngine(rbac=RBACEngine(roles=(founder,)))

    def _approval_policy_engine(self) -> PolicyEngine:
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
            rbac=RBACEngine(roles=(sales_rep,)),
            approval_rules=(
                approval_required(
                    object_type="account",
                    action=PermissionAction.UPDATE,
                    fields=("metadata",),
                    required_approvers=("sales_manager",),
                    reason="Account metadata changes require sales manager approval.",
                ),
            ),
        )

    def _approval_map(self) -> GitHubApprovalMap:
        return GitHubApprovalMap(
            entries=(
                GitHubApprovalOwner(subject="sales_manager", owners=("@sabbanis",)),
            )
        )

    def _github_review_data(self):
        return {
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

    def _account(self, stage: AccountStage, metadata=None) -> CRMAccount:
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


class RecordingRunner:
    """Fake command runner for GitHub CLI adapter tests."""

    def __init__(self) -> None:
        self.calls: list[CommandResult] = []
        self.issue_state = "open"

    def run(self, args, cwd: Path, check: bool = True) -> CommandResult:
        command = tuple(args)
        result = self._result(command)
        self.calls.append(result)
        if check and result.returncode != 0:
            raise GitHubPublishError(result.stderr or result.stdout or "command failed")
        return result

    def _result(self, command: tuple[str, ...]) -> CommandResult:
        if command[:4] == ("git", "diff", "--cached", "--quiet"):
            return CommandResult(args=command, returncode=1)
        if command[:3] == ("gh", "pr", "view") and command[3].startswith("http"):
            return CommandResult(args=command, returncode=0, stdout=self._pr_json())
        if command[:3] == ("gh", "pr", "view"):
            return CommandResult(args=command, returncode=1, stderr="not found")
        if command[:3] == ("gh", "pr", "create"):
            return CommandResult(
                args=command,
                returncode=0,
                stdout="https://github.com/acme/opra.ai/pull/42\n",
            )
        if command[:3] == ("gh", "issue", "create"):
            return CommandResult(
                args=command,
                returncode=0,
                stdout="https://github.com/acme/opra.ai/issues/99\n",
            )
        if command[:3] == ("gh", "issue", "close"):
            self.issue_state = "closed"
            return CommandResult(args=command, returncode=0)
        if command[:3] == ("gh", "issue", "reopen"):
            self.issue_state = "open"
            return CommandResult(args=command, returncode=0)
        if command[:3] == ("gh", "issue", "edit"):
            return CommandResult(args=command, returncode=0)
        if command[:3] == ("gh", "issue", "view"):
            return CommandResult(args=command, returncode=0, stdout=self._issue_json())
        return CommandResult(args=command, returncode=0)

    def _pr_json(self) -> str:
        return (
            '{"number": 42, "title": "Update account", "body": "Body", '
            '"headRefName": "opra-ai/proposals/proposal_a", '
            '"baseRefName": "main", '
            '"url": "https://github.com/acme/opra.ai/pull/42"}'
        )

    def _issue_json(self) -> str:
        state = self.issue_state.upper()
        return (
            '{"number": 99, "title": "Customer-impacting defect: Acme", '
            '"body": "Triaged.", '
            f'"state": "{state}", '
            '"labels": [{"name": "defect"}, {"name": "triaged"}], '
            '"assignees": [{"login": "ssabbani"}, {"login": "manager"}], '
            '"url": "https://github.com/acme/opra.ai/issues/99"}'
        )


if __name__ == "__main__":
    unittest.main()
