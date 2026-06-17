"""GitHub adapter boundary and proposal PR publishing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any, Mapping, Optional, Sequence

from company_os_core.audit import AuditEventWriter, WrittenAuditEvent
from company_os_core.models import (
    ApprovalDecision,
    AuditAction,
    EventResult,
    PermissionAction,
    SourceInterface,
    utc_now,
)
from company_os_core.proposals import (
    APPROVED_DECISION,
    MutationProposal,
    MutationProposalApproval,
    MutationProposalStatus,
)
from company_os_core.serialization import read_yaml, stable_hash, to_yaml, write_yaml


DEFAULT_GITHUB_APPROVAL_OWNERS_PATH = Path(
    "platform/integrations/github/approval_owners.yaml"
)
DEFAULT_GITHUB_ISSUE_PREVIEW_DIR = Path("platform/integrations/github/issue_previews")
DEFAULT_GITHUB_MESSAGE_THREAD_DIR = Path("platform/integrations/github/message_threads")
DEFAULT_GITHUB_PR_PREVIEW_DIR = Path("platform/integrations/github/pr_previews")
PROPOSAL_PR_REPORT_MARKER = "<!-- opra-ai-proposal-check -->"


@dataclass(frozen=True)
class GitHubFileChange:
    """One file change to commit to a GitHub branch."""

    path: str
    content: str


@dataclass(frozen=True)
class GitHubCommitResult:
    """Result of committing files through a GitHub adapter."""

    branch: str
    message: str
    file_paths: tuple[str, ...]


@dataclass(frozen=True)
class GitHubPullRequestResult:
    """Result of opening a pull request through a GitHub adapter."""

    number: int
    title: str
    body: str
    head_branch: str
    base_branch: str
    url: str


@dataclass(frozen=True)
class GitHubIssueResult:
    """Result of creating or updating a GitHub issue."""

    number: int
    title: str
    body: str
    state: str
    labels: tuple[str, ...] = field(default_factory=tuple)
    assignees: tuple[str, ...] = field(default_factory=tuple)
    url: str = ""


@dataclass(frozen=True)
class GitHubPullRequestCommentResult:
    """Result of creating or reading a pull-request conversation comment."""

    id: str
    body: str
    author: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: str = ""


@dataclass(frozen=True)
class ProposalPRValidationIssue:
    """One proposal PR validation issue."""

    field: str
    message: str


@dataclass(frozen=True)
class ProposalPRValidationResult:
    """Result of validating a proposal PR checkout."""

    valid: bool
    issues: tuple[ProposalPRValidationIssue, ...] = field(default_factory=tuple)

    @classmethod
    def ok(cls) -> "ProposalPRValidationResult":
        return cls(valid=True)

    @classmethod
    def failed(cls, issues: list[ProposalPRValidationIssue]) -> "ProposalPRValidationResult":
        return cls(valid=False, issues=tuple(issues))


@dataclass(frozen=True)
class CommandResult:
    """Result returned by a command runner."""

    args: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class PublishedProposalPullRequest:
    """Published proposal PR payload and adapter result."""

    proposal_id: str
    branch_name: str
    base_branch: str
    commit: GitHubCommitResult
    pull_request: GitHubPullRequestResult
    files: tuple[GitHubFileChange, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecordedProposalMerge:
    """Proposal merge evidence recorded after a PR lands on the base branch."""

    proposal_path: Path
    proposal: MutationProposal
    target_path: Path
    audit_event: WrittenAuditEvent


@dataclass(frozen=True)
class GitHubApprovalOwner:
    """Mapping from one opra.ai approver subject to GitHub owners."""

    subject: str
    owners: tuple[str, ...]


@dataclass(frozen=True)
class GitHubApprovalMap:
    """Configured subject-to-GitHub-owner mappings."""

    entries: tuple[GitHubApprovalOwner, ...] = field(default_factory=tuple)

    def owners_for_subject(self, subject: str) -> tuple[str, ...]:
        """Return GitHub owners configured for one opra.ai subject."""

        for entry in self.entries:
            if entry.subject == subject:
                return entry.owners
        if subject.startswith("@"):
            return (subject,)
        if subject.startswith("github:"):
            return (subject.removeprefix("github:"),)
        return ()


@dataclass(frozen=True)
class GitHubPullRequestReview:
    """One GitHub pull-request review entry."""

    reviewer: str
    state: str
    submitted_at: Optional[datetime] = None


@dataclass(frozen=True)
class GitHubProposalApprovalEvidence:
    """Proposal approval evidence derived from GitHub pull-request reviews."""

    proposal_id: str
    pull_request_number: Optional[int]
    pull_request_url: str
    required_approvers: tuple[str, ...]
    satisfied_approvers: tuple[str, ...]
    missing_approvers: tuple[str, ...]
    approvals: tuple[MutationProposalApproval, ...]


class GitHubPublishError(ValueError):
    """Raised when a proposal cannot be published as a GitHub PR."""


class GitHubAdapter:
    """Interface for GitHub repository operations."""

    def create_branch(self, branch_name: str, base_branch: str) -> None:
        """Create or ensure a branch from a base branch."""

        raise NotImplementedError

    def commit_files(
        self,
        branch_name: str,
        message: str,
        files: tuple[GitHubFileChange, ...],
    ) -> GitHubCommitResult:
        """Commit file changes to a branch."""

        raise NotImplementedError

    def open_pull_request(
        self,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> GitHubPullRequestResult:
        """Open or return a pull request for a branch."""

        raise NotImplementedError

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubIssueResult:
        """Create a GitHub issue."""

        raise NotImplementedError

    def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubIssueResult:
        """Update a GitHub issue."""

        raise NotImplementedError

    def request_pull_request_reviewers(
        self,
        number: int,
        reviewers: tuple[str, ...],
    ) -> None:
        """Request GitHub users or teams as pull-request participants."""

        raise NotImplementedError

    def create_pull_request_comment(
        self,
        number: int,
        body: str,
    ) -> GitHubPullRequestCommentResult:
        """Create a timeline comment on a pull request."""

        raise NotImplementedError

    def list_pull_request_comments(
        self,
        number: int,
    ) -> tuple[GitHubPullRequestCommentResult, ...]:
        """List timeline comments on a pull request."""

        raise NotImplementedError


class CommandRunner:
    """Command runner interface for real GitHub CLI integration."""

    def run(
        self,
        args: Sequence[str],
        cwd: Path,
        check: bool = True,
    ) -> CommandResult:
        """Run one command."""

        raise NotImplementedError


class SubprocessCommandRunner(CommandRunner):
    """Subprocess-backed command runner."""

    def run(
        self,
        args: Sequence[str],
        cwd: Path,
        check: bool = True,
    ) -> CommandResult:
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        result = CommandResult(
            args=tuple(args),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if check and result.returncode != 0:
            raise GitHubPublishError(_command_error(result))
        return result


class MockGitHubAdapter(GitHubAdapter):
    """Deterministic in-memory adapter for local tests and dry-run CLI flows."""

    def __init__(self, repo_url: str = "https://github.com/local/opra.ai") -> None:
        self.repo_url = repo_url.rstrip("/")
        self.branches: dict[str, str] = {}
        self.commits: list[GitHubCommitResult] = []
        self.pull_requests: list[GitHubPullRequestResult] = []
        self.issues: dict[int, GitHubIssueResult] = {}
        self.pull_request_reviewers: dict[int, tuple[str, ...]] = {}
        self.pull_request_comments: dict[int, list[GitHubPullRequestCommentResult]] = {}

    def create_branch(self, branch_name: str, base_branch: str) -> None:
        self.branches.setdefault(branch_name, base_branch)

    def commit_files(
        self,
        branch_name: str,
        message: str,
        files: tuple[GitHubFileChange, ...],
    ) -> GitHubCommitResult:
        if branch_name not in self.branches:
            raise GitHubPublishError(f"branch has not been created: {branch_name}")
        if not files:
            raise GitHubPublishError("commit must include at least one file")

        result = GitHubCommitResult(
            branch=branch_name,
            message=message,
            file_paths=tuple(file.path for file in files),
        )
        self.commits.append(result)
        return result

    def open_pull_request(
        self,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> GitHubPullRequestResult:
        for pull_request in self.pull_requests:
            if (
                pull_request.head_branch == branch_name
                and pull_request.base_branch == base_branch
            ):
                return pull_request

        number = len(self.pull_requests) + 1
        result = GitHubPullRequestResult(
            number=number,
            title=title,
            body=body,
            head_branch=branch_name,
            base_branch=base_branch,
            url=f"{self.repo_url}/pull/{number}",
        )
        self.pull_requests.append(result)
        return result

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubIssueResult:
        title = _required_text("title", title)
        labels = _clean_tuple(labels)
        assignees = _clean_tuple(assignees)
        number = len(self.issues) + 1
        result = GitHubIssueResult(
            number=number,
            title=title,
            body=body,
            state="open",
            labels=labels,
            assignees=assignees,
            url=f"{self.repo_url}/issues/{number}",
        )
        self.issues[number] = result
        return result

    def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubIssueResult:
        if number not in self.issues:
            raise GitHubPublishError(f"issue does not exist: {number}")
        existing = self.issues[number]
        updated = replace(
            existing,
            title=_required_text("title", title) if title is not None else existing.title,
            body=body if body is not None else existing.body,
            state=_normalize_issue_state(state) if state is not None else existing.state,
            labels=_unique_values(existing.labels + _clean_tuple(labels)),
            assignees=_unique_values(existing.assignees + _clean_tuple(assignees)),
        )
        self.issues[number] = updated
        return updated

    def seed_issue(self, issue: GitHubIssueResult) -> None:
        """Load an issue into the mock adapter for local preview updates."""

        if issue.number < 1:
            raise GitHubPublishError("issue number must be positive")
        self.issues[issue.number] = issue

    def seed_pull_request(self, pull_request: GitHubPullRequestResult) -> None:
        """Load a pull request into the mock adapter for local preview updates."""

        if pull_request.number < 1:
            raise GitHubPublishError("pull request number must be positive")
        if not any(existing.number == pull_request.number for existing in self.pull_requests):
            self.pull_requests.append(pull_request)
            self.pull_requests.sort(key=lambda item: item.number)

    def seed_pull_request_comment(
        self,
        number: int,
        comment: GitHubPullRequestCommentResult,
    ) -> None:
        """Load a pull-request comment into the mock adapter for local preview updates."""

        pull_request_number = _positive_issue_number(number)
        self.pull_request_comments.setdefault(pull_request_number, []).append(comment)

    def request_pull_request_reviewers(
        self,
        number: int,
        reviewers: tuple[str, ...],
    ) -> None:
        pull_request_number = _positive_issue_number(number)
        existing = self.pull_request_reviewers.get(pull_request_number, ())
        self.pull_request_reviewers[pull_request_number] = _unique_values(
            existing + _clean_tuple(reviewers)
        )

    def create_pull_request_comment(
        self,
        number: int,
        body: str,
    ) -> GitHubPullRequestCommentResult:
        pull_request_number = _positive_issue_number(number)
        comments = self.pull_request_comments.setdefault(pull_request_number, [])
        comment_number = len(comments) + 1
        result = GitHubPullRequestCommentResult(
            id=str(comment_number),
            body=_required_text("body", body),
            author="",
            created_at=utc_now(),
            updated_at=utc_now(),
            url=f"{self.repo_url}/pull/{pull_request_number}#issuecomment-{comment_number}",
        )
        comments.append(result)
        return result

    def list_pull_request_comments(
        self,
        number: int,
    ) -> tuple[GitHubPullRequestCommentResult, ...]:
        pull_request_number = _positive_issue_number(number)
        return tuple(self.pull_request_comments.get(pull_request_number, []))


class GitHubCLIAdapter(GitHubAdapter):
    """GitHub adapter backed by local `git` and `gh` commands."""

    def __init__(
        self,
        repo_root: Path,
        runner: Optional[CommandRunner] = None,
        remote: str = "origin",
        git_bin: str = "git",
        gh_bin: str = "gh",
    ) -> None:
        self._repo_root = repo_root
        self._runner = runner or SubprocessCommandRunner()
        self._remote = remote
        self._git_bin = git_bin
        self._gh_bin = gh_bin

    def create_branch(self, branch_name: str, base_branch: str) -> None:
        self._run_git("fetch", self._remote, base_branch)
        self._run_git(
            "switch",
            "-C",
            branch_name,
            f"{self._remote}/{base_branch}",
        )

    def commit_files(
        self,
        branch_name: str,
        message: str,
        files: tuple[GitHubFileChange, ...],
    ) -> GitHubCommitResult:
        if not files:
            raise GitHubPublishError("commit must include at least one file")

        file_paths = tuple(file.path for file in files)
        for file in files:
            path = _safe_repo_path(repo_root=self._repo_root, relative_path=file.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(file.content, encoding="utf-8")

        self._run_git("add", "--", *file_paths)
        diff = self._run_git("diff", "--cached", "--quiet", "--", *file_paths, check=False)
        if diff.returncode == 1:
            self._run_git("commit", "-m", message)
        elif diff.returncode != 0:
            raise GitHubPublishError(_command_error(diff))

        self._run_git("push", "-u", self._remote, branch_name)
        return GitHubCommitResult(
            branch=branch_name,
            message=message,
            file_paths=file_paths,
        )

    def open_pull_request(
        self,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> GitHubPullRequestResult:
        existing = self._view_pull_request(branch_name, check=False)
        if existing is not None:
            return existing

        created = self._run_gh(
            "pr",
            "create",
            "--base",
            base_branch,
            "--head",
            branch_name,
            "--title",
            title,
            "--body",
            body,
        )
        pr_ref = _last_stdout_line(created) or branch_name
        viewed = self._view_pull_request(pr_ref, check=True)
        if viewed is None:
            raise GitHubPublishError("GitHub CLI did not return pull request details")
        return viewed

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubIssueResult:
        args = [
            "issue",
            "create",
            "--title",
            _required_text("title", title),
            "--body",
            body,
        ]
        for label in _clean_tuple(labels):
            args.extend(("--label", label))
        for assignee in _clean_tuple(assignees):
            args.extend(("--assignee", assignee))

        created = self._run_gh(*args)
        issue_ref = _last_stdout_line(created)
        if not issue_ref:
            raise GitHubPublishError("GitHub CLI did not return issue details")
        viewed = self._view_issue(issue_ref, check=True)
        if viewed is None:
            raise GitHubPublishError("GitHub CLI did not return issue details")
        return viewed

    def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: tuple[str, ...] = (),
        assignees: tuple[str, ...] = (),
    ) -> GitHubIssueResult:
        issue_number = _positive_issue_number(number)
        edit_args = ["issue", "edit", str(issue_number)]
        if title is not None:
            edit_args.extend(("--title", _required_text("title", title)))
        if body is not None:
            edit_args.extend(("--body", body))
        for label in _clean_tuple(labels):
            edit_args.extend(("--add-label", label))
        for assignee in _clean_tuple(assignees):
            edit_args.extend(("--add-assignee", assignee))

        if len(edit_args) > 3:
            self._run_gh(*edit_args)

        if state is not None:
            normalized_state = _normalize_issue_state(state)
            if normalized_state == "closed":
                self._run_gh("issue", "close", str(issue_number))
            else:
                self._run_gh("issue", "reopen", str(issue_number))

        viewed = self._view_issue(str(issue_number), check=True)
        if viewed is None:
            raise GitHubPublishError("GitHub CLI did not return issue details")
        return viewed

    def request_pull_request_reviewers(
        self,
        number: int,
        reviewers: tuple[str, ...],
    ) -> None:
        pull_request_number = _positive_issue_number(number)
        for reviewer in _clean_tuple(reviewers):
            self._run_gh("pr", "edit", str(pull_request_number), "--add-reviewer", reviewer)

    def create_pull_request_comment(
        self,
        number: int,
        body: str,
    ) -> GitHubPullRequestCommentResult:
        pull_request_number = _positive_issue_number(number)
        cleaned_body = _required_text("body", body)
        created = self._run_gh(
            "pr",
            "comment",
            str(pull_request_number),
            "--body",
            cleaned_body,
        )
        url = _last_stdout_line(created)
        return GitHubPullRequestCommentResult(
            id=_comment_id_from_url(url),
            body=cleaned_body,
            url=url,
        )

    def list_pull_request_comments(
        self,
        number: int,
    ) -> tuple[GitHubPullRequestCommentResult, ...]:
        pull_request_number = _positive_issue_number(number)
        result = self._run_gh(
            "pr",
            "view",
            str(pull_request_number),
            "--json",
            "comments",
        )
        return _pull_request_comments_from_json(result.stdout)

    def _view_pull_request(self, pr_ref: str, check: bool) -> Optional[GitHubPullRequestResult]:
        result = self._run_gh(
            "pr",
            "view",
            pr_ref,
            "--json",
            "number,title,body,headRefName,baseRefName,url",
            check=check,
        )
        if result.returncode != 0:
            return None
        return _pull_request_from_json(result.stdout)

    def _view_issue(self, issue_ref: str, check: bool) -> Optional[GitHubIssueResult]:
        result = self._run_gh(
            "issue",
            "view",
            issue_ref,
            "--json",
            "number,title,body,state,labels,assignees,url",
            check=check,
        )
        if result.returncode != 0:
            return None
        return _issue_from_json(result.stdout)

    def _run_git(self, *args: str, check: bool = True) -> CommandResult:
        return self._runner.run((self._git_bin, *args), cwd=self._repo_root, check=check)

    def _run_gh(self, *args: str, check: bool = True) -> CommandResult:
        return self._runner.run((self._gh_bin, *args), cwd=self._repo_root, check=check)


class GitHubProposalPublisher:
    """Publish mutation proposals through a GitHub adapter boundary."""

    def __init__(self, adapter: GitHubAdapter, repo_root: Path) -> None:
        self._adapter = adapter
        self._repo_root = repo_root

    def publish(
        self,
        proposal: MutationProposal,
        proposal_path: Path,
        base_branch: str = "main",
    ) -> PublishedProposalPullRequest:
        """Publish a proposal as a pull-request payload."""

        _validate_publishable(proposal)
        branch_name = _branch_name(proposal.id)
        files = _proposal_files(
            repo_root=self._repo_root,
            proposal=proposal,
            proposal_path=proposal_path,
        )
        title = _pr_title(proposal)
        body = _pr_body(proposal)
        message = f"{title}\n\nProposal: {proposal.id}"

        self._adapter.create_branch(branch_name=branch_name, base_branch=base_branch)
        commit = self._adapter.commit_files(
            branch_name=branch_name,
            message=message,
            files=files,
        )
        pull_request = self._adapter.open_pull_request(
            branch_name=branch_name,
            base_branch=base_branch,
            title=title,
            body=body,
        )
        return PublishedProposalPullRequest(
            proposal_id=proposal.id,
            branch_name=branch_name,
            base_branch=base_branch,
            commit=commit,
            pull_request=pull_request,
            files=files,
        )


class ProposalPRValidator:
    """Validate proposal pull-request artifacts in a checked-out repository."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def validate(
        self,
        proposal: MutationProposal,
        proposal_path: Path,
        approval_evidence: Optional[GitHubProposalApprovalEvidence] = None,
    ) -> ProposalPRValidationResult:
        """Validate one proposal and its target file."""

        issues: list[ProposalPRValidationIssue] = []
        self._validate_status(proposal, issues)
        self._validate_action(proposal, issues)
        self._validate_after_snapshot(proposal, issues)
        self._validate_before_hash(proposal, issues)
        self._validate_proposal_path(proposal_path, issues)
        self._validate_target_file(proposal, issues)
        self._validate_required_approvals(proposal, approval_evidence, issues)

        if issues:
            return ProposalPRValidationResult.failed(issues)
        return ProposalPRValidationResult.ok()

    def _validate_status(
        self,
        proposal: MutationProposal,
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        if proposal.status in (MutationProposalStatus.REJECTED, MutationProposalStatus.APPLIED):
            issues.append(
                ProposalPRValidationIssue(
                    field="status",
                    message=f"proposal status {proposal.status.value} cannot be reviewed",
                )
            )

    def _validate_action(
        self,
        proposal: MutationProposal,
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        if proposal.action not in (PermissionAction.CREATE, PermissionAction.UPDATE):
            issues.append(
                ProposalPRValidationIssue(
                    field="action",
                    message=f"unsupported proposal action: {proposal.action.value}",
                )
            )

    def _validate_after_snapshot(
        self,
        proposal: MutationProposal,
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        if not proposal.after:
            issues.append(ProposalPRValidationIssue("after", "after snapshot is required"))
            return
        if proposal.after_hash != stable_hash(proposal.after):
            issues.append(
                ProposalPRValidationIssue(
                    field="after_hash",
                    message="after_hash does not match after snapshot",
                )
            )

    def _validate_before_hash(
        self,
        proposal: MutationProposal,
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        if proposal.action == PermissionAction.UPDATE and not proposal.before_hash:
            issues.append(
                ProposalPRValidationIssue(
                    field="before_hash",
                    message="update proposals must include before_hash",
                )
            )
        if proposal.action == PermissionAction.CREATE and proposal.before_hash:
            issues.append(
                ProposalPRValidationIssue(
                    field="before_hash",
                    message="create proposals must not include before_hash",
                )
            )

    def _validate_proposal_path(
        self,
        proposal_path: Path,
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        try:
            proposal_path.resolve().relative_to(self._repo_root.resolve())
        except ValueError:
            issues.append(
                ProposalPRValidationIssue(
                    field="proposal_path",
                    message="proposal path must be inside repository root",
                )
            )

    def _validate_target_file(
        self,
        proposal: MutationProposal,
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        try:
            target_path = _safe_repo_path(
                repo_root=self._repo_root,
                relative_path=proposal.target_path,
            )
        except GitHubPublishError as exc:
            issues.append(ProposalPRValidationIssue("target_path", str(exc)))
            return

        if not target_path.exists():
            issues.append(
                ProposalPRValidationIssue(
                    field="target_path",
                    message=f"target file does not exist: {proposal.target_path}",
                )
            )
            return

        target_data = read_yaml(target_path)
        if not isinstance(target_data, dict):
            issues.append(
                ProposalPRValidationIssue(
                    field="target_path",
                    message="target file must contain a YAML object",
                )
            )
            return

        if stable_hash(target_data) != proposal.after_hash:
            issues.append(
                ProposalPRValidationIssue(
                    field="target_path",
                    message="target file content does not match proposal after_hash",
                )
            )
        if str(target_data.get("object_type", "")) != proposal.object_type:
            issues.append(
                ProposalPRValidationIssue(
                    field="target_path.object_type",
                    message="target object_type does not match proposal",
                )
            )
        if str(target_data.get("id", "")) != proposal.object_id:
            issues.append(
                ProposalPRValidationIssue(
                    field="target_path.id",
                    message="target id does not match proposal",
                )
            )

    def _validate_required_approvals(
        self,
        proposal: MutationProposal,
        approval_evidence: Optional[GitHubProposalApprovalEvidence],
        issues: list[ProposalPRValidationIssue],
    ) -> None:
        approvals = proposal.approvals
        if approval_evidence is not None:
            approvals = _merge_approvals(approvals, approval_evidence.approvals)

        missing = _unmet_required_approvers(proposal, approvals)
        if missing:
            issues.append(
                ProposalPRValidationIssue(
                    field="approvals",
                    message="missing required approvals: " + ", ".join(missing),
                )
            )


class ProposalMergeRecorder:
    """Record audit evidence for a proposal already merged through GitHub."""

    def __init__(self, repo_root: Path, audit_writer: AuditEventWriter) -> None:
        self._repo_root = repo_root
        self._audit_writer = audit_writer

    def record(
        self,
        proposal: MutationProposal,
        proposal_path: Path,
        actor: str = "github-actions",
        approval_evidence: Optional[GitHubProposalApprovalEvidence] = None,
    ) -> RecordedProposalMerge:
        """Mark a merged proposal applied and record audit evidence.

        GitHub PR publishing commits the target object's proposed state on the PR branch.
        After the PR is merged, this recorder verifies that the source object already equals
        the proposal's after snapshot, then records evidence without rewriting the target.
        """

        actor = actor.strip()
        if not actor:
            raise GitHubPublishError("actor is required")

        validation = ProposalPRValidator(repo_root=self._repo_root).validate(
            proposal=proposal,
            proposal_path=proposal_path,
            approval_evidence=approval_evidence,
        )
        if not validation.valid:
            reasons = "; ".join(
                f"{issue.field}: {issue.message}" for issue in validation.issues
            )
            raise GitHubPublishError(f"proposal merge validation failed: {reasons}")

        target_path = _safe_repo_path(
            repo_root=self._repo_root,
            relative_path=proposal.target_path,
        )
        approvals = proposal.approvals
        if approval_evidence is not None:
            approvals = _merge_approvals(approvals, approval_evidence.approvals)
        now = utc_now()
        audit_event = self._audit_writer.record_mutation(
            actor=actor,
            action=_audit_action_for(proposal.action),
            object_type=proposal.object_type,
            object_id=proposal.object_id,
            source_interface=SourceInterface.GITHUB,
            request_id=proposal.request_id,
            before=proposal.before,
            after=proposal.after,
            result=EventResult.COMPLETED,
            approval_chain=_audit_approval_chain(approvals),
        )
        updated = replace(
            proposal,
            status=MutationProposalStatus.APPLIED,
            approvals=approvals,
            approved_at=proposal.approved_at or (now if approvals else None),
            applied_at=now,
            applied_by=actor,
            audit_event_id=audit_event.event.event_id,
        )
        write_yaml(proposal_path, updated)
        return RecordedProposalMerge(
            proposal_path=proposal_path,
            proposal=updated,
            target_path=target_path,
            audit_event=audit_event,
        )


def _validate_publishable(proposal: MutationProposal) -> None:
    if proposal.status in (MutationProposalStatus.REJECTED, MutationProposalStatus.APPLIED):
        raise GitHubPublishError(
            f"proposal {proposal.id} cannot be published with status {proposal.status.value}"
        )
    if proposal.action not in (PermissionAction.CREATE, PermissionAction.UPDATE):
        raise GitHubPublishError(f"unsupported proposal action: {proposal.action.value}")
    if not proposal.after:
        raise GitHubPublishError("proposal is missing after snapshot")
    if proposal.after_hash != stable_hash(proposal.after):
        raise GitHubPublishError("proposal after_hash does not match after snapshot")


def read_github_approval_map(
    repo_root: Path,
    path: Path = DEFAULT_GITHUB_APPROVAL_OWNERS_PATH,
) -> GitHubApprovalMap:
    """Read configured GitHub owner mappings for opra.ai approver subjects."""

    mapping_path = path if path.is_absolute() else repo_root / path
    if not mapping_path.exists():
        return GitHubApprovalMap()
    return github_approval_map_from_data(read_yaml(mapping_path))


def github_approval_map_from_data(data: Any) -> GitHubApprovalMap:
    """Parse a GitHub approval owner mapping document."""

    if not isinstance(data, Mapping):
        raise GitHubPublishError("GitHub approval map must contain a YAML object")

    subjects = data.get("subjects", [])
    entries: list[GitHubApprovalOwner] = []
    if isinstance(subjects, Mapping):
        for subject, value in subjects.items():
            entries.append(_approval_owner_from_mapping_item(str(subject), value))
    elif isinstance(subjects, list):
        for item in subjects:
            if not isinstance(item, Mapping):
                raise GitHubPublishError("approval map subject entry must be an object")
            subject = str(item.get("subject", "")).strip()
            if not subject:
                raise GitHubPublishError("approval map subject is required")
            entries.append(_approval_owner_from_mapping_item(subject, item))
    else:
        raise GitHubPublishError("approval map subjects must be a list or object")

    return GitHubApprovalMap(entries=tuple(entries))


def github_approval_evidence_from_pull_request_data(
    proposal: MutationProposal,
    data: Any,
    approval_map: GitHubApprovalMap,
) -> GitHubProposalApprovalEvidence:
    """Build proposal approval evidence from a GitHub PR JSON payload."""

    pull_request_number = None
    pull_request_url = ""
    if isinstance(data, Mapping):
        pull_request_number = _optional_int(data.get("number"))
        pull_request_url = str(data.get("url", ""))

    reviews = github_reviews_from_pull_request_data(data)
    approvals = _proposal_approvals_from_github_reviews(
        proposal=proposal,
        reviews=reviews,
        approval_map=approval_map,
        pull_request_number=pull_request_number,
        pull_request_url=pull_request_url,
    )
    combined = _merge_approvals(proposal.approvals, approvals)
    missing = _unmet_required_approvers(proposal, combined)
    missing_set = set(missing)
    satisfied = tuple(
        approver
        for approver in proposal.required_approvers
        if approver not in missing_set
    )
    return GitHubProposalApprovalEvidence(
        proposal_id=proposal.id,
        pull_request_number=pull_request_number,
        pull_request_url=pull_request_url,
        required_approvers=proposal.required_approvers,
        satisfied_approvers=satisfied,
        missing_approvers=missing,
        approvals=approvals,
    )


def github_reviews_from_pull_request_data(data: Any) -> tuple[GitHubPullRequestReview, ...]:
    """Parse GitHub PR review data from `gh pr view --json number,url,reviews`."""

    if isinstance(data, Mapping):
        reviews = data.get("reviews", [])
    else:
        reviews = data
    if reviews is None or reviews == {}:
        return ()
    if not isinstance(reviews, list):
        raise GitHubPublishError("GitHub reviews payload must be a list")

    parsed = []
    for item in reviews:
        if not isinstance(item, Mapping):
            raise GitHubPublishError("GitHub review entry must be an object")
        reviewer = _reviewer_login(item)
        if not reviewer:
            continue
        parsed.append(
            GitHubPullRequestReview(
                reviewer=reviewer,
                state=str(item.get("state", "")).upper(),
                submitted_at=_optional_timestamp(
                    item.get("submittedAt", item.get("submitted_at"))
                ),
            )
        )
    return tuple(parsed)


def render_proposal_pr_validation_report(
    proposal: MutationProposal,
    result: ProposalPRValidationResult,
    proposal_path: Optional[Path] = None,
    approval_evidence: Optional[GitHubProposalApprovalEvidence] = None,
) -> str:
    """Render a Markdown report for GitHub Actions summaries and PR comments."""

    status = "passed" if result.valid else "failed"
    lines = [
        PROPOSAL_PR_REPORT_MARKER,
        "## opra.ai Proposal Check",
        "",
        f"- Status: `{status}`",
        f"- Proposal: `{proposal.id}`",
        f"- Object: `{proposal.object_type}/{proposal.object_id}`",
        f"- Action: `{proposal.action.value}`",
        f"- Target: `{proposal.target_path}`",
        f"- Policy decision: `{proposal.policy_decision.value}`",
        "",
        "### Approval Evidence",
        "",
        f"- Required approvers: {_inline_list(proposal.required_approvers)}",
        f"- Satisfied approvers: {_inline_list(_satisfied_approvers(proposal, approval_evidence))}",
        f"- Missing approvers: {_inline_list(_missing_approvers(proposal, approval_evidence))}",
    ]
    if approval_evidence is not None and approval_evidence.pull_request_url:
        lines.append(f"- Pull request: {approval_evidence.pull_request_url}")

    lines.extend(
        (
            "",
            "### Validation Issues",
            "",
        )
    )
    if result.issues:
        lines.extend(
            f"- `{issue.field}`: {issue.message}"
            for issue in result.issues
        )
    else:
        lines.append("- None")

    lines.extend(
        (
            "",
            "### Source Integrity",
            "",
            f"- Before hash: `{proposal.before_hash or 'not applicable'}`",
            f"- After hash: `{proposal.after_hash}`",
            "",
        )
    )
    if proposal_path is not None:
        lines.insert(5, f"- Proposal file: `{proposal_path}`")
    return "\n".join(lines)


def _satisfied_approvers(
    proposal: MutationProposal,
    approval_evidence: Optional[GitHubProposalApprovalEvidence],
) -> tuple[str, ...]:
    missing = set(_missing_approvers(proposal, approval_evidence))
    return tuple(
        approver
        for approver in proposal.required_approvers
        if approver not in missing
    )


def _missing_approvers(
    proposal: MutationProposal,
    approval_evidence: Optional[GitHubProposalApprovalEvidence],
) -> tuple[str, ...]:
    approvals = proposal.approvals
    if approval_evidence is not None:
        approvals = _merge_approvals(approvals, approval_evidence.approvals)
    return _unmet_required_approvers(proposal, approvals)


def _inline_list(values: tuple[str, ...]) -> str:
    if not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)


def _proposal_files(
    repo_root: Path,
    proposal: MutationProposal,
    proposal_path: Path,
) -> tuple[GitHubFileChange, ...]:
    proposal_repo_path = _relative_path(repo_root=repo_root, path=proposal_path)
    return (
        GitHubFileChange(path=proposal.target_path, content=to_yaml(proposal.after)),
        GitHubFileChange(path=proposal_repo_path, content=to_yaml(proposal)),
    )


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _safe_repo_path(repo_root: Path, relative_path: str) -> Path:
    candidate = repo_root / relative_path
    try:
        candidate.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise GitHubPublishError(f"file path escapes repository root: {relative_path}") from exc
    return candidate


def _branch_name(proposal_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9._/-]+", "-", proposal_id.strip())
    safe_id = safe_id.replace("..", ".").strip("./-")
    if not safe_id:
        raise GitHubPublishError("proposal id cannot produce a branch name")
    return f"opra-ai/proposals/{safe_id}"


def _pr_title(proposal: MutationProposal) -> str:
    action = _action_label(proposal.action)
    return f"[opra.ai] {action} {proposal.object_type} {proposal.object_id}"


def _action_label(action: PermissionAction) -> str:
    if action == PermissionAction.CREATE:
        return "Create"
    if action == PermissionAction.UPDATE:
        return "Update"
    return action.value.title()


def _pr_body(proposal: MutationProposal) -> str:
    required_approvers = _markdown_list(proposal.required_approvers)
    reasons = _markdown_list(proposal.reasons)
    before_hash = proposal.before_hash or "not applicable"
    return "\n".join(
        (
            "## Proposal",
            "",
            f"- ID: `{proposal.id}`",
            f"- Status: `{proposal.status.value}`",
            f"- Action: `{proposal.action.value}`",
            f"- Object: `{proposal.object_type}/{proposal.object_id}`",
            f"- Target: `{proposal.target_path}`",
            "",
            "## Policy",
            "",
            f"- Decision: `{proposal.policy_decision.value}`",
            "- Required approvers:",
            required_approvers,
            "- Reasons:",
            reasons,
            "",
            "## Source Integrity",
            "",
            f"- Before hash: `{before_hash}`",
            f"- After hash: `{proposal.after_hash}`",
        )
    )


def _markdown_list(values: tuple[str, ...]) -> str:
    if not values:
        return "  - None"
    return "\n".join(f"  - {value}" for value in values)


def _pull_request_from_json(document: str) -> GitHubPullRequestResult:
    try:
        data = json.loads(document)
    except json.JSONDecodeError as exc:
        raise GitHubPublishError("GitHub CLI returned invalid pull request JSON") from exc

    return GitHubPullRequestResult(
        number=int(data["number"]),
        title=str(data["title"]),
        body=str(data.get("body", "")),
        head_branch=str(data["headRefName"]),
        base_branch=str(data["baseRefName"]),
        url=str(data["url"]),
    )


def _issue_from_json(document: str) -> GitHubIssueResult:
    try:
        data = json.loads(document)
    except json.JSONDecodeError as exc:
        raise GitHubPublishError("GitHub CLI returned invalid issue JSON") from exc

    return _issue_from_mapping(data)


def _pull_request_comments_from_json(document: str) -> tuple[GitHubPullRequestCommentResult, ...]:
    try:
        data = json.loads(document)
    except json.JSONDecodeError as exc:
        raise GitHubPublishError("GitHub CLI returned invalid pull request comments JSON") from exc

    comments = data.get("comments", data)
    if comments is None or comments == {}:
        return ()
    if not isinstance(comments, list):
        raise GitHubPublishError("GitHub pull request comments payload must be a list")

    parsed = []
    for item in comments:
        if not isinstance(item, Mapping):
            raise GitHubPublishError("GitHub pull request comment entry must be an object")
        url = str(item.get("url", ""))
        parsed.append(
            GitHubPullRequestCommentResult(
                id=str(item.get("id", "")) or _comment_id_from_url(url),
                body=str(item.get("body", "")),
                author=_comment_author(item),
                created_at=_optional_timestamp(item.get("createdAt", item.get("created_at"))),
                updated_at=_optional_timestamp(item.get("updatedAt", item.get("updated_at"))),
                url=url,
            )
        )
    return tuple(parsed)


def issue_from_data(data: Any) -> GitHubIssueResult:
    """Parse a serialized GitHub issue result."""

    if not isinstance(data, Mapping):
        raise GitHubPublishError("GitHub issue data must contain an object")
    return _issue_from_mapping(data)


def _issue_from_mapping(data: Mapping[str, Any]) -> GitHubIssueResult:
    return GitHubIssueResult(
        number=int(data["number"]),
        title=str(data["title"]),
        body=str(data.get("body", "")),
        state=_normalize_issue_state(str(data.get("state", "open"))),
        labels=_label_names(data.get("labels", [])),
        assignees=_assignee_logins(data.get("assignees", [])),
        url=str(data.get("url", "")),
    )


def _last_stdout_line(result: CommandResult) -> str:
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _comment_id_from_url(url: str) -> str:
    match = re.search(r"(?:issuecomment-|discussion_r)([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else ""


def _comment_author(item: Mapping[str, Any]) -> str:
    author = item.get("author", item.get("user", {}))
    if isinstance(author, Mapping):
        return str(author.get("login", ""))
    return str(author or "")


def _command_error(result: CommandResult) -> str:
    command = " ".join(result.args)
    details = result.stderr.strip() or result.stdout.strip() or "command failed"
    return f"{command} failed with exit code {result.returncode}: {details}"


def _required_text(field_name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise GitHubPublishError(f"{field_name} is required")
    return cleaned


def _clean_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values if str(value).strip())


def _unique_values(values: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _positive_issue_number(number: int) -> int:
    issue_number = int(number)
    if issue_number < 1:
        raise GitHubPublishError("issue number must be positive")
    return issue_number


def _normalize_issue_state(state: str) -> str:
    normalized = state.strip().lower()
    if normalized in ("open", "opened"):
        return "open"
    if normalized in ("closed", "close"):
        return "closed"
    raise GitHubPublishError(f"unsupported issue state: {state}")


def _label_names(value: Any) -> tuple[str, ...]:
    if value is None or value == {}:
        return ()
    if not isinstance(value, list):
        raise GitHubPublishError("issue labels must be a list")
    labels = []
    for item in value:
        if isinstance(item, Mapping):
            labels.append(str(item.get("name", "")).strip())
        else:
            labels.append(str(item).strip())
    return _clean_tuple(tuple(labels))


def _assignee_logins(value: Any) -> tuple[str, ...]:
    if value is None or value == {}:
        return ()
    if not isinstance(value, list):
        raise GitHubPublishError("issue assignees must be a list")
    assignees = []
    for item in value:
        if isinstance(item, Mapping):
            assignees.append(str(item.get("login", "")).strip())
        else:
            assignees.append(str(item).strip())
    return _clean_tuple(tuple(assignees))


def _audit_approval_chain(
    approvals: tuple[MutationProposalApproval, ...],
) -> tuple[ApprovalDecision, ...]:
    return tuple(
        ApprovalDecision(
            approver=approval.approver,
            decision=approval.decision,
            timestamp=approval.timestamp,
        )
        for approval in approvals
    )


def _audit_action_for(action: PermissionAction) -> AuditAction:
    if action == PermissionAction.CREATE:
        return AuditAction.CREATE
    if action == PermissionAction.UPDATE:
        return AuditAction.UPDATE
    raise GitHubPublishError(f"unsupported proposal action: {action.value}")


def _approval_owner_from_mapping_item(subject: str, value: Any) -> GitHubApprovalOwner:
    if isinstance(value, Mapping):
        owners = value.get("owners", [])
    else:
        owners = value
    if not isinstance(owners, list):
        raise GitHubPublishError(f"approval owners for {subject} must be a list")
    parsed = tuple(str(owner).strip() for owner in owners if str(owner).strip())
    if not parsed:
        raise GitHubPublishError(f"approval owners for {subject} cannot be empty")
    return GitHubApprovalOwner(subject=subject, owners=parsed)


def _proposal_approvals_from_github_reviews(
    proposal: MutationProposal,
    reviews: tuple[GitHubPullRequestReview, ...],
    approval_map: GitHubApprovalMap,
    pull_request_number: Optional[int],
    pull_request_url: str,
) -> tuple[MutationProposalApproval, ...]:
    if not proposal.required_approvers:
        return ()

    approvals = []
    approved_reviews = tuple(
        review for review in _latest_reviews_by_reviewer(reviews) if review.state == "APPROVED"
    )
    for required_approver in proposal.required_approvers:
        owners = approval_map.owners_for_subject(required_approver)
        review = _first_review_for_owners(approved_reviews, owners)
        if review is None:
            continue
        owner_subjects = tuple(f"github:{_display_github_owner(owner)}" for owner in owners)
        approvals.append(
            MutationProposalApproval(
                approver=_display_github_owner(review.reviewer),
                decision=APPROVED_DECISION,
                timestamp=review.submitted_at or utc_now(),
                subjects=(required_approver, *owners, *owner_subjects),
                reason=_github_review_reason(
                    pull_request_number=pull_request_number,
                    pull_request_url=pull_request_url,
                ),
            )
        )
    return tuple(approvals)


def _latest_reviews_by_reviewer(
    reviews: tuple[GitHubPullRequestReview, ...],
) -> tuple[GitHubPullRequestReview, ...]:
    latest: dict[str, tuple[int, GitHubPullRequestReview]] = {}
    for index, review in enumerate(reviews):
        key = _normalize_github_owner(review.reviewer)
        current = latest.get(key)
        if current is None or _review_is_newer(review, index, current[1], current[0]):
            latest[key] = (index, review)
    return tuple(item[1] for item in latest.values())


def _review_is_newer(
    candidate: GitHubPullRequestReview,
    candidate_index: int,
    current: GitHubPullRequestReview,
    current_index: int,
) -> bool:
    if candidate.submitted_at is not None and current.submitted_at is not None:
        return candidate.submitted_at >= current.submitted_at
    if candidate.submitted_at is not None:
        return True
    if current.submitted_at is not None:
        return False
    return candidate_index >= current_index


def _first_review_for_owners(
    reviews: tuple[GitHubPullRequestReview, ...],
    owners: tuple[str, ...],
) -> Optional[GitHubPullRequestReview]:
    normalized_owners = {_normalize_github_owner(owner) for owner in owners}
    for review in reviews:
        if _normalize_github_owner(review.reviewer) in normalized_owners:
            return review
    return None


def _unmet_required_approvers(
    proposal: MutationProposal,
    approvals: tuple[MutationProposalApproval, ...],
) -> tuple[str, ...]:
    approved_subjects = {
        subject
        for approval in approvals
        if approval.decision == APPROVED_DECISION
        for subject in approval.subjects
    }
    return tuple(
        required_approver
        for required_approver in proposal.required_approvers
        if required_approver not in approved_subjects
    )


def _merge_approvals(
    existing: tuple[MutationProposalApproval, ...],
    incoming: tuple[MutationProposalApproval, ...],
) -> tuple[MutationProposalApproval, ...]:
    merged = list(existing)
    seen = {
        (
            approval.approver,
            approval.decision,
            approval.timestamp.isoformat(),
            approval.subjects,
        )
        for approval in existing
    }
    for approval in incoming:
        key = (
            approval.approver,
            approval.decision,
            approval.timestamp.isoformat(),
            approval.subjects,
        )
        if key not in seen:
            merged.append(approval)
            seen.add(key)
    return tuple(merged)


def _github_review_reason(
    pull_request_number: Optional[int],
    pull_request_url: str,
) -> str:
    if pull_request_url:
        return f"GitHub pull-request approval evidence: {pull_request_url}"
    if pull_request_number is not None:
        return f"GitHub pull-request approval evidence: PR #{pull_request_number}"
    return "GitHub pull-request approval evidence."


def _reviewer_login(item: Mapping[str, Any]) -> str:
    author = item.get("author", item.get("user"))
    if isinstance(author, Mapping):
        return str(author.get("login", "")).strip()
    return str(item.get("login", item.get("reviewer", ""))).strip()


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _optional_timestamp(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _normalize_github_owner(value: str) -> str:
    return value.strip().removeprefix("github:").lstrip("@").lower()


def _display_github_owner(value: str) -> str:
    normalized = value.strip().removeprefix("github:")
    if normalized.startswith("@"):
        return normalized
    return f"@{normalized}"
