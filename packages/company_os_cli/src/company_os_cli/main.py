"""opra.ai command-line interface."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from company_os_core import (
    AccountStage,
    ApprovalStatus,
    AuditAction,
    AuditEventWriter,
    BaseObject,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    DEFAULT_GITHUB_PR_PREVIEW_DIR,
    DEFAULT_GITHUB_APPROVAL_OWNERS_PATH,
    DEFAULT_GITHUB_ISSUE_PREVIEW_DIR,
    EventResult,
    GitHubCLIAdapter,
    GitHubProposalPublisher,
    GovernedMutationService,
    LocalObjectStore,
    MockGitHubAdapter,
    MutationProposalService,
    ObjectLink,
    OpportunityStage,
    Permission,
    PermissionAction,
    PolicyDecision,
    ProposalMergeRecorder,
    ProposalPRValidator,
    Role,
    SourceInterface,
    User,
    __version__,
    account_schema,
    approval_required,
    crm_lifecycle_validator,
    crm_skill_descriptors,
    github_approval_evidence_from_pull_request_data,
    issue_from_data,
    opportunity_schema,
    read_github_approval_map,
    render_proposal_pr_validation_report,
    run_crm_skill,
    write_crm_read_model,
)
from company_os_core.models import ObjectStatus, ObjectVisibility
from company_os_core.policy import PolicyEngine
from company_os_core.project import PRODUCT_NAME, missing_required_paths
from company_os_core.rbac import RBACEngine
from company_os_core.schema import base_object_schema, validate_object
from company_os_core.serialization import read_yaml, to_json, write_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opra", description=f"{PRODUCT_NAME} CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subcommands = parser.add_subparsers(dest="command")

    doctor = subcommands.add_parser("doctor", help="Check the local repository foundation.")
    doctor.add_argument(
        "--repo-root",
        default=".",
        help="Path to the opra.ai repository root. Defaults to the current directory.",
    )

    validate = subcommands.add_parser("validate", help="Validate a source-of-truth object file.")
    validate.add_argument("--file", required=True, help="Path to the YAML object file.")

    inspect = subcommands.add_parser("inspect", help="Print a parsed object file as JSON.")
    inspect.add_argument("--file", required=True, help="Path to the YAML object file.")

    policy = subcommands.add_parser("policy-check", help="Run a local RBAC and approval check.")
    policy.add_argument("--file", required=True, help="Path to the YAML object file.")
    policy.add_argument("--user", required=True, help="Username or user ID.")
    policy.add_argument("--role", action="append", default=[], help="Role ID. Can be repeated.")
    policy.add_argument(
        "--action",
        required=True,
        choices=[action.value for action in PermissionAction],
        help="Action to evaluate.",
    )
    policy.add_argument(
        "--field",
        action="append",
        default=[],
        help="Field being changed. Can be repeated.",
    )

    audit = subcommands.add_parser("audit-record", help="Write an append-only audit event.")
    audit.add_argument(
        "--event-dir",
        default="platform/audit/events",
        help="Directory for audit event YAML files.",
    )
    audit.add_argument("--actor", required=True, help="Actor responsible for the event.")
    audit.add_argument(
        "--action",
        required=True,
        choices=[action.value for action in AuditAction],
        help="Audit action.",
    )
    audit.add_argument("--object-type", required=True, help="Object type being audited.")
    audit.add_argument("--object-id", required=True, help="Object ID being audited.")
    audit.add_argument(
        "--source-interface",
        default=SourceInterface.CLI.value,
        choices=[source.value for source in SourceInterface],
        help="Interface that initiated the event.",
    )
    audit.add_argument("--request-id", required=True, help="Request identifier for traceability.")
    audit.add_argument("--before-file", help="Optional YAML snapshot before the mutation.")
    audit.add_argument("--after-file", help="Optional YAML snapshot after the mutation.")
    audit.add_argument(
        "--result",
        default=EventResult.COMPLETED.value,
        choices=[result.value for result in EventResult],
        help="Audit event result.",
    )

    governed = subcommands.add_parser(
        "governed-write",
        help="Validate, authorize, store, and audit an object file.",
    )
    governed.add_argument("--file", required=True, help="Path to the YAML object file.")
    governed.add_argument("--repo-root", default=".", help="Repository root for object storage.")
    governed.add_argument(
        "--event-dir",
        default="platform/audit/events",
        help="Audit event directory.",
    )
    governed.add_argument("--user", required=True, help="Username or user ID.")
    governed.add_argument("--role", action="append", default=[], help="Role ID. Can be repeated.")
    governed.add_argument(
        "--action",
        default=PermissionAction.CREATE.value,
        choices=[PermissionAction.CREATE.value, PermissionAction.UPDATE.value],
        help="Governed mutation action.",
    )
    governed.add_argument(
        "--request-id",
        required=True,
        help="Request identifier for traceability.",
    )
    governed.add_argument("--field", action="append", default=[], help="Changed field for updates.")

    proposal = subcommands.add_parser(
        "propose-mutation",
        help="Validate, authorize, and write a reviewable mutation proposal.",
    )
    proposal.add_argument("--file", required=True, help="Path to the YAML object file.")
    proposal.add_argument("--repo-root", default=".", help="Repository root for object storage.")
    proposal.add_argument("--user", required=True, help="Username or user ID.")
    proposal.add_argument("--role", action="append", default=[], help="Role ID. Can be repeated.")
    proposal.add_argument(
        "--action",
        default=PermissionAction.UPDATE.value,
        choices=[PermissionAction.CREATE.value, PermissionAction.UPDATE.value],
        help="Proposed mutation action.",
    )
    proposal.add_argument(
        "--request-id",
        required=True,
        help="Request identifier for traceability.",
    )
    proposal.add_argument("--field", action="append", default=[], help="Changed field.")

    approve_proposal = subcommands.add_parser(
        "approve-proposal",
        help="Approve a reviewable mutation proposal.",
    )
    approve_proposal.add_argument("--file", required=True, help="Path to the proposal YAML file.")
    approve_proposal.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for object storage.",
    )
    approve_proposal.add_argument("--user", required=True, help="Username or user ID.")
    approve_proposal.add_argument(
        "--role",
        action="append",
        default=[],
        help="Role ID. Can be repeated.",
    )
    approve_proposal.add_argument("--reason", default="", help="Optional approval reason.")

    reject_proposal = subcommands.add_parser(
        "reject-proposal",
        help="Reject a reviewable mutation proposal.",
    )
    reject_proposal.add_argument("--file", required=True, help="Path to the proposal YAML file.")
    reject_proposal.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for object storage.",
    )
    reject_proposal.add_argument("--user", required=True, help="Username or user ID.")
    reject_proposal.add_argument(
        "--role",
        action="append",
        default=[],
        help="Role ID. Can be repeated.",
    )
    reject_proposal.add_argument("--reason", default="", help="Optional rejection reason.")

    apply_proposal = subcommands.add_parser(
        "apply-proposal",
        help="Apply an approved mutation proposal and write audit evidence.",
    )
    apply_proposal.add_argument("--file", required=True, help="Path to the proposal YAML file.")
    apply_proposal.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for object storage.",
    )
    apply_proposal.add_argument(
        "--event-dir",
        default="platform/audit/events",
        help="Audit event directory.",
    )
    apply_proposal.add_argument("--user", required=True, help="Username or user ID.")
    apply_proposal.add_argument(
        "--role",
        action="append",
        default=[],
        help="Role ID. Can be repeated.",
    )

    publish_pr = subcommands.add_parser(
        "publish-proposal-pr",
        help="Build a mock GitHub pull-request payload for a mutation proposal.",
    )
    publish_pr.add_argument("--file", required=True, help="Path to the proposal YAML file.")
    publish_pr.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for object storage.",
    )
    publish_pr.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for the pull request.",
    )
    publish_pr.add_argument(
        "--repo-url",
        default="https://github.com/local/opra.ai",
        help="Repository URL used in the mock pull-request result.",
    )
    publish_pr.add_argument(
        "--preview-dir",
        default=str(DEFAULT_GITHUB_PR_PREVIEW_DIR),
        help="Directory for local mock PR preview artifacts.",
    )
    publish_pr.add_argument(
        "--real",
        action="store_true",
        help="Publish with local git and GitHub CLI instead of the mock adapter.",
    )
    publish_pr.add_argument(
        "--remote",
        default="origin",
        help="Git remote used by --real publishing.",
    )

    create_issue = subcommands.add_parser(
        "create-github-issue",
        help="Create a mock GitHub issue preview or a real GitHub issue.",
    )
    create_issue.add_argument("--title", required=True, help="GitHub issue title.")
    create_issue.add_argument("--body", default="", help="GitHub issue body.")
    create_issue.add_argument(
        "--label",
        action="append",
        default=[],
        help="Issue label. Can be repeated.",
    )
    create_issue.add_argument(
        "--assignee",
        action="append",
        default=[],
        help="Issue assignee. Can be repeated.",
    )
    create_issue.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for real GitHub CLI calls and mock previews.",
    )
    create_issue.add_argument(
        "--repo-url",
        default="https://github.com/local/opra.ai",
        help="Repository URL used in the mock issue result.",
    )
    create_issue.add_argument(
        "--preview-dir",
        default=str(DEFAULT_GITHUB_ISSUE_PREVIEW_DIR),
        help="Directory for local mock issue preview artifacts.",
    )
    create_issue.add_argument(
        "--real",
        action="store_true",
        help="Create a real GitHub issue with the GitHub CLI.",
    )

    update_issue = subcommands.add_parser(
        "update-github-issue",
        help="Update a mock GitHub issue preview or a real GitHub issue.",
    )
    update_issue.add_argument("--number", required=True, type=int, help="GitHub issue number.")
    update_issue.add_argument("--title", help="Optional replacement issue title.")
    update_issue.add_argument("--body", help="Optional replacement issue body.")
    update_issue.add_argument(
        "--state",
        choices=("open", "closed"),
        help="Optional issue state.",
    )
    update_issue.add_argument(
        "--label",
        action="append",
        default=[],
        help="Issue label to add. Can be repeated.",
    )
    update_issue.add_argument(
        "--assignee",
        action="append",
        default=[],
        help="Issue assignee to add. Can be repeated.",
    )
    update_issue.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for real GitHub CLI calls and mock previews.",
    )
    update_issue.add_argument(
        "--repo-url",
        default="https://github.com/local/opra.ai",
        help="Repository URL used in the mock issue result.",
    )
    update_issue.add_argument(
        "--preview-dir",
        default=str(DEFAULT_GITHUB_ISSUE_PREVIEW_DIR),
        help="Directory for local mock issue preview artifacts.",
    )
    update_issue.add_argument(
        "--real",
        action="store_true",
        help="Update a real GitHub issue with the GitHub CLI.",
    )

    validate_pr = subcommands.add_parser(
        "validate-proposal-pr",
        help="Validate a mutation proposal and target file in a PR checkout.",
    )
    validate_pr.add_argument("--file", required=True, help="Path to the proposal YAML file.")
    validate_pr.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for target file validation.",
    )
    validate_pr.add_argument(
        "--github-review-file",
        help="Optional GitHub PR review JSON/YAML file from gh pr view.",
    )
    validate_pr.add_argument(
        "--approval-map",
        default=str(DEFAULT_GITHUB_APPROVAL_OWNERS_PATH),
        help="Path to the GitHub approval owner mapping file.",
    )
    validate_pr.add_argument(
        "--report-file",
        help="Optional path for a Markdown validation report.",
    )

    record_merge = subcommands.add_parser(
        "record-proposal-merge",
        help="Record audit evidence for a proposal merged through GitHub.",
    )
    record_merge.add_argument("--file", required=True, help="Path to the proposal YAML file.")
    record_merge.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for target file validation.",
    )
    record_merge.add_argument(
        "--event-dir",
        default="platform/audit/events",
        help="Audit event directory.",
    )
    record_merge.add_argument(
        "--actor",
        default="github-actions",
        help="Actor recorded on the audit event.",
    )
    record_merge.add_argument(
        "--github-review-file",
        help="Optional GitHub PR review JSON/YAML file from gh pr view.",
    )
    record_merge.add_argument(
        "--approval-map",
        default=str(DEFAULT_GITHUB_APPROVAL_OWNERS_PATH),
        help="Path to the GitHub approval owner mapping file.",
    )

    index_crm = subcommands.add_parser(
        "index-crm",
        help="Build the local CRM dashboard read model.",
    )
    index_crm.add_argument(
        "--repo-root",
        default=".",
        help="Path to the opra.ai repository root. Defaults to the current directory.",
    )
    index_crm.add_argument(
        "--output",
        help="Optional output path. Defaults to platform/dashboards/read_models/crm_summary.json.",
    )

    crm_skill = subcommands.add_parser(
        "crm-skill",
        help="Run a local CRM Skill handler.",
    )
    crm_skill.add_argument(
        "--name",
        required=True,
        choices=[descriptor.name for descriptor in crm_skill_descriptors()],
        help="CRM Skill name.",
    )
    crm_skill.add_argument(
        "--repo-root",
        default=".",
        help="Path to the opra.ai repository root. Defaults to the current directory.",
    )
    crm_skill.add_argument("--user", required=True, help="Username or user ID.")
    crm_skill.add_argument("--role", action="append", default=[], help="Role ID. Can be repeated.")
    crm_skill.add_argument("--account-id", default="", help="Optional CRM account ID filter.")
    crm_skill.add_argument("--limit", type=int, default=5, help="Maximum rows to return.")

    return parser


def run_doctor(repo_root: Path) -> int:
    missing_paths = missing_required_paths(repo_root)
    if missing_paths:
        print("opra.ai repository check failed.")
        print("Missing required paths:")
        for missing_path in missing_paths:
            print(f"- {missing_path}")
        return 1

    print("opra.ai repository check passed.")
    return 0


def run_validate(file_path: Path) -> int:
    try:
        data = _read_object_file(file_path)
    except (OSError, ValueError) as exc:
        print(f"Validation failed: {exc}")
        return 1

    object_type = str(data.get("object_type", ""))
    schema = _schema_for_object_type(object_type)
    result = validate_object(data, schema)
    if result.valid:
        print(f"Validation passed: {file_path}")
        return 0

    print(f"Validation failed: {file_path}")
    for issue in result.issues:
        print(f"- {issue.field}: {issue.message}")
    return 1


def run_inspect(file_path: Path) -> int:
    try:
        data = _read_object_file(file_path)
    except (OSError, ValueError) as exc:
        print(f"Inspect failed: {exc}")
        return 1

    print(to_json(data))
    return 0


def run_policy_check(
    file_path: Path,
    username: str,
    roles: tuple[str, ...],
    action: PermissionAction,
    fields: tuple[str, ...],
) -> int:
    try:
        data = _read_object_file(file_path)
    except (OSError, ValueError) as exc:
        print(f"Policy check failed: {exc}")
        return 1

    engine = _demo_policy_engine()
    user = User(id=username, username=username, roles=roles)
    result = engine.evaluate(user=user, action=action, obj=data, fields=fields)

    print(f"Decision: {result.decision.value}")
    for reason in result.reasons:
        print(f"- {reason}")
    if result.required_approvers:
        print("Required approvers:")
        for approver in result.required_approvers:
            print(f"- {approver}")

    return 0 if result.decision != PolicyDecision.DENY else 1


def run_audit_record(
    event_dir: Path,
    actor: str,
    action: AuditAction,
    object_type: str,
    object_id: str,
    source_interface: SourceInterface,
    request_id: str,
    result: EventResult,
    before_file: Optional[Path],
    after_file: Optional[Path],
) -> int:
    try:
        before = read_yaml(before_file) if before_file is not None else None
        after = read_yaml(after_file) if after_file is not None else None
        written = AuditEventWriter(event_dir).record_mutation(
            actor=actor,
            action=action,
            object_type=object_type,
            object_id=object_id,
            source_interface=source_interface,
            request_id=request_id,
            before=before,
            after=after,
            result=result,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Audit record failed: {exc}")
        return 1

    print(f"Audit event written: {written.path}")
    print(f"Event id: {written.event.event_id}")
    if written.event.before_hash is not None:
        print(f"Before hash: {written.event.before_hash}")
    if written.event.after_hash is not None:
        print(f"After hash: {written.event.after_hash}")
    return 0


def run_governed_write(
    file_path: Path,
    repo_root: Path,
    event_dir: Path,
    username: str,
    roles: tuple[str, ...],
    action: PermissionAction,
    request_id: str,
    fields: tuple[str, ...],
) -> int:
    try:
        data = _read_object_file(file_path)
        obj = _object_from_data(data)
        store = LocalObjectStore(repo_root, path_map=_demo_path_map())
        service = GovernedMutationService(
            object_store=store,
            policy_engine=_demo_policy_engine(),
            audit_writer=AuditEventWriter(event_dir),
            domain_validators=(crm_lifecycle_validator,),
        )
        user = User(id=username, username=username, roles=roles)
        schema = _schema_for_object_type(obj.object_type)

        if action == PermissionAction.CREATE:
            result = service.create_object(
                user=user,
                obj=obj,
                schema=schema,
                request_id=request_id,
            )
        else:
            before = _read_before_state(store, obj.object_type, obj.id)
            result = service.update_object(
                user=user,
                before=before,
                after=obj,
                schema=schema,
                fields=fields,
                request_id=request_id,
            )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Governed write failed: {exc}")
        return 1

    print(f"Decision: {result.policy_result.decision.value}")
    for reason in result.policy_result.reasons:
        print(f"- {reason}")
    if result.policy_result.required_approvers:
        print("Required approvers:")
        for approver in result.policy_result.required_approvers:
            print(f"- {approver}")
    print(f"Audit event: {result.audit_event.path}")
    if result.committed and result.stored_object is not None:
        print(f"Stored object: {result.stored_object.path}")

    return 0 if result.policy_result.decision != PolicyDecision.DENY else 1


def run_propose_mutation(
    file_path: Path,
    repo_root: Path,
    username: str,
    roles: tuple[str, ...],
    action: PermissionAction,
    request_id: str,
    fields: tuple[str, ...],
) -> int:
    try:
        data = _read_object_file(file_path)
        obj = _object_from_data(data)
        store = LocalObjectStore(repo_root, path_map=_demo_path_map())
        service = _proposal_service(repo_root)
        before = (
            None
            if action == PermissionAction.CREATE
            else store.read_object(obj.object_type, obj.id).data
        )
        written = service.propose(
            user=User(id=username, username=username, roles=roles),
            action=action,
            before=before,
            after=obj,
            schema=_schema_for_object_type(obj.object_type),
            fields=fields,
            request_id=request_id,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Proposal failed: {exc}")
        return 1

    proposal = written.proposal
    print(f"Proposal written: {written.path}")
    print(f"Proposal id: {proposal.id}")
    print(f"Decision: {proposal.policy_decision.value}")
    if proposal.required_approvers:
        print("Required approvers:")
        for approver in proposal.required_approvers:
            print(f"- {approver}")
    return 0


def run_approve_proposal(
    file_path: Path,
    repo_root: Path,
    username: str,
    roles: tuple[str, ...],
    reason: str,
) -> int:
    try:
        service = _proposal_service(repo_root)
        written = service.approve(
            path=file_path,
            user=User(id=username, username=username, roles=roles),
            reason=reason,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Proposal approval failed: {exc}")
        return 1

    proposal = written.proposal
    print(f"Proposal status: {proposal.status.value}")
    print(f"Approvals: {len(proposal.approvals)}")
    remaining = service.remaining_approvers(proposal)
    if remaining:
        print("Remaining approvers:")
        for approver in remaining:
            print(f"- {approver}")
    return 0


def run_reject_proposal(
    file_path: Path,
    repo_root: Path,
    username: str,
    roles: tuple[str, ...],
    reason: str,
) -> int:
    try:
        written = _proposal_service(repo_root).reject(
            path=file_path,
            user=User(id=username, username=username, roles=roles),
            reason=reason,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Proposal rejection failed: {exc}")
        return 1

    print(f"Proposal status: {written.proposal.status.value}")
    if written.proposal.rejection_reason:
        print(f"Reason: {written.proposal.rejection_reason}")
    return 0


def run_apply_proposal(
    file_path: Path,
    repo_root: Path,
    event_dir: Path,
    username: str,
    roles: tuple[str, ...],
) -> int:
    try:
        service = _proposal_service(repo_root)
        proposal = service.read_proposal(file_path)
        applied = service.apply(
            path=file_path,
            user=User(id=username, username=username, roles=roles),
            schema=_schema_for_object_type(proposal.object_type),
            audit_writer=AuditEventWriter(event_dir),
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Proposal apply failed: {exc}")
        return 1

    print(f"Proposal status: {applied.proposal.status.value}")
    print(f"Stored object: {applied.target_path}")
    print(f"Audit event: {applied.audit_event.path}")
    return 0


def run_publish_proposal_pr(
    file_path: Path,
    repo_root: Path,
    base_branch: str,
    repo_url: str,
    preview_dir: Path,
    real: bool,
    remote: str,
) -> int:
    try:
        proposal = _proposal_service(repo_root).read_proposal(file_path)
        adapter = (
            GitHubCLIAdapter(repo_root=repo_root, remote=remote)
            if real
            else MockGitHubAdapter(repo_url=repo_url)
        )
        publisher = GitHubProposalPublisher(
            adapter=adapter,
            repo_root=repo_root,
        )
        published = publisher.publish(
            proposal=proposal,
            proposal_path=file_path,
            base_branch=base_branch,
        )
        preview_path = None
        if not real:
            preview_path = _preview_path(
                repo_root=repo_root,
                preview_dir=preview_dir,
                proposal_id=proposal.id,
            )
            write_yaml(preview_path, published)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Proposal PR publish failed: {exc}")
        return 1

    if preview_path is not None:
        print(f"PR preview written: {preview_path}")
    print(f"Branch: {published.branch_name}")
    print(f"Pull request: {published.pull_request.url}")
    return 0


def run_create_github_issue(
    repo_root: Path,
    title: str,
    body: str,
    labels: tuple[str, ...],
    assignees: tuple[str, ...],
    repo_url: str,
    preview_dir: Path,
    real: bool,
) -> int:
    try:
        adapter = (
            GitHubCLIAdapter(repo_root=repo_root)
            if real
            else MockGitHubAdapter(repo_url=repo_url)
        )
        issue = adapter.create_issue(
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
        )
        preview_path = None
        if not real:
            preview_path = _issue_preview_path(
                repo_root=repo_root,
                preview_dir=preview_dir,
                issue_number=issue.number,
            )
            write_yaml(preview_path, issue)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"GitHub issue create failed: {exc}")
        return 1

    if preview_path is not None:
        print(f"Issue preview written: {preview_path}")
    _print_github_issue(issue)
    return 0


def run_update_github_issue(
    repo_root: Path,
    number: int,
    title: Optional[str],
    body: Optional[str],
    state: Optional[str],
    labels: tuple[str, ...],
    assignees: tuple[str, ...],
    repo_url: str,
    preview_dir: Path,
    real: bool,
) -> int:
    try:
        adapter = (
            GitHubCLIAdapter(repo_root=repo_root)
            if real
            else MockGitHubAdapter(repo_url=repo_url)
        )
        if not real and isinstance(adapter, MockGitHubAdapter):
            adapter.seed_issue(
                _read_issue_preview(
                    repo_root=repo_root,
                    preview_dir=preview_dir,
                    issue_number=number,
                )
            )
        issue = adapter.update_issue(
            number=number,
            title=title,
            body=body,
            state=state,
            labels=labels,
            assignees=assignees,
        )
        preview_path = None
        if not real:
            preview_path = _issue_preview_path(
                repo_root=repo_root,
                preview_dir=preview_dir,
                issue_number=issue.number,
            )
            write_yaml(preview_path, issue)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"GitHub issue update failed: {exc}")
        return 1

    if preview_path is not None:
        print(f"Issue preview written: {preview_path}")
    _print_github_issue(issue)
    return 0


def run_validate_proposal_pr(
    file_path: Path,
    repo_root: Path,
    github_review_file: Optional[Path],
    approval_map_path: Path,
    report_file: Optional[Path],
) -> int:
    try:
        proposal = _proposal_service(repo_root).read_proposal(file_path)
        approval_evidence = _github_approval_evidence(
            proposal=proposal,
            repo_root=repo_root,
            github_review_file=github_review_file,
            approval_map_path=approval_map_path,
        )
        result = ProposalPRValidator(repo_root=repo_root).validate(
            proposal=proposal,
            proposal_path=file_path,
            approval_evidence=approval_evidence,
        )
        if report_file is not None:
            _write_proposal_pr_report(
                report_file=report_file,
                proposal=proposal,
                proposal_path=_repo_display_path(repo_root=repo_root, path=file_path),
                result=result,
                approval_evidence=approval_evidence,
            )
    except (OSError, ValueError) as exc:
        print(f"Proposal PR validation failed: {exc}")
        return 1

    if result.valid:
        print(f"Proposal PR validation passed: {file_path}")
        if approval_evidence is not None:
            _print_github_approval_evidence(approval_evidence)
        return 0

    print(f"Proposal PR validation failed: {file_path}")
    if approval_evidence is not None:
        _print_github_approval_evidence(approval_evidence)
    for issue in result.issues:
        print(f"- {issue.field}: {issue.message}")
    return 1


def run_record_proposal_merge(
    file_path: Path,
    repo_root: Path,
    event_dir: Path,
    actor: str,
    github_review_file: Optional[Path],
    approval_map_path: Path,
) -> int:
    try:
        proposal = _proposal_service(repo_root).read_proposal(file_path)
        approval_evidence = _github_approval_evidence(
            proposal=proposal,
            repo_root=repo_root,
            github_review_file=github_review_file,
            approval_map_path=approval_map_path,
        )
        recorded = ProposalMergeRecorder(
            repo_root=repo_root,
            audit_writer=AuditEventWriter(event_dir),
        ).record(
            proposal=proposal,
            proposal_path=file_path,
            actor=actor,
            approval_evidence=approval_evidence,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"Proposal merge record failed: {exc}")
        return 1

    print(f"Proposal status: {recorded.proposal.status.value}")
    print(f"Target object: {recorded.target_path}")
    print(f"Audit event: {recorded.audit_event.path}")
    if approval_evidence is not None:
        _print_github_approval_evidence(approval_evidence)
    return 0


def run_index_crm(repo_root: Path, output_path: Optional[Path]) -> int:
    try:
        written = write_crm_read_model(repo_root=repo_root, output_path=output_path)
    except (OSError, ValueError) as exc:
        print(f"CRM index failed: {exc}")
        return 1

    summary = written.read_model.summary
    print(f"CRM read model written: {written.path}")
    print(f"Accounts: {summary.account_count}")
    print(f"Opportunities: {summary.opportunity_count}")
    print(f"Total ARR: {summary.total_arr}")
    print(f"Open pipeline: {summary.open_pipeline_amount}")
    print(f"Weighted pipeline: {summary.weighted_pipeline_amount}")
    return 0


def run_crm_skill_command(
    name: str,
    repo_root: Path,
    username: str,
    roles: tuple[str, ...],
    account_id: str,
    limit: int,
) -> int:
    try:
        result = run_crm_skill(
            name=name,
            repo_root=repo_root,
            user=User(id=username, username=username, roles=roles),
            policy_engine=_demo_policy_engine(),
            inputs={"account_id": account_id, "limit": limit},
        )
    except (OSError, ValueError) as exc:
        print(f"CRM Skill failed: {exc}")
        return 1

    print(f"Skill: {result.name}")
    print(f"Decision: {result.decision.value}")
    print(f"Summary: {result.summary}")
    if result.reasons:
        print("Reasons:")
        for reason in result.reasons:
            print(f"- {reason}")
    if result.data:
        print(to_json(result.data))
    return 0 if result.allowed else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor(Path(args.repo_root).resolve())
    if args.command == "validate":
        return run_validate(Path(args.file).resolve())
    if args.command == "inspect":
        return run_inspect(Path(args.file).resolve())
    if args.command == "policy-check":
        return run_policy_check(
            file_path=Path(args.file).resolve(),
            username=args.user,
            roles=tuple(args.role),
            action=PermissionAction(args.action),
            fields=tuple(args.field),
        )
    if args.command == "audit-record":
        return run_audit_record(
            event_dir=Path(args.event_dir).resolve(),
            actor=args.actor,
            action=AuditAction(args.action),
            object_type=args.object_type,
            object_id=args.object_id,
            source_interface=SourceInterface(args.source_interface),
            request_id=args.request_id,
            result=EventResult(args.result),
            before_file=Path(args.before_file).resolve() if args.before_file else None,
            after_file=Path(args.after_file).resolve() if args.after_file else None,
        )
    if args.command == "governed-write":
        return run_governed_write(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            event_dir=Path(args.event_dir).resolve(),
            username=args.user,
            roles=tuple(args.role),
            action=PermissionAction(args.action),
            request_id=args.request_id,
            fields=tuple(args.field),
        )
    if args.command == "propose-mutation":
        return run_propose_mutation(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            username=args.user,
            roles=tuple(args.role),
            action=PermissionAction(args.action),
            request_id=args.request_id,
            fields=tuple(args.field),
        )
    if args.command == "approve-proposal":
        return run_approve_proposal(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            username=args.user,
            roles=tuple(args.role),
            reason=args.reason,
        )
    if args.command == "reject-proposal":
        return run_reject_proposal(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            username=args.user,
            roles=tuple(args.role),
            reason=args.reason,
        )
    if args.command == "apply-proposal":
        return run_apply_proposal(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            event_dir=Path(args.event_dir).resolve(),
            username=args.user,
            roles=tuple(args.role),
        )
    if args.command == "publish-proposal-pr":
        return run_publish_proposal_pr(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            base_branch=args.base_branch,
            repo_url=args.repo_url,
            preview_dir=Path(args.preview_dir),
            real=args.real,
            remote=args.remote,
        )
    if args.command == "create-github-issue":
        return run_create_github_issue(
            repo_root=Path(args.repo_root).resolve(),
            title=args.title,
            body=args.body,
            labels=tuple(args.label),
            assignees=tuple(args.assignee),
            repo_url=args.repo_url,
            preview_dir=Path(args.preview_dir),
            real=args.real,
        )
    if args.command == "update-github-issue":
        return run_update_github_issue(
            repo_root=Path(args.repo_root).resolve(),
            number=args.number,
            title=args.title,
            body=args.body,
            state=args.state,
            labels=tuple(args.label),
            assignees=tuple(args.assignee),
            repo_url=args.repo_url,
            preview_dir=Path(args.preview_dir),
            real=args.real,
        )
    if args.command == "validate-proposal-pr":
        return run_validate_proposal_pr(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            github_review_file=(
                Path(args.github_review_file).resolve()
                if args.github_review_file
                else None
            ),
            approval_map_path=Path(args.approval_map),
            report_file=Path(args.report_file).resolve() if args.report_file else None,
        )
    if args.command == "record-proposal-merge":
        return run_record_proposal_merge(
            file_path=Path(args.file).resolve(),
            repo_root=Path(args.repo_root).resolve(),
            event_dir=Path(args.event_dir).resolve(),
            actor=args.actor,
            github_review_file=(
                Path(args.github_review_file).resolve()
                if args.github_review_file
                else None
            ),
            approval_map_path=Path(args.approval_map),
        )
    if args.command == "index-crm":
        return run_index_crm(
            repo_root=Path(args.repo_root).resolve(),
            output_path=Path(args.output).resolve() if args.output else None,
        )
    if args.command == "crm-skill":
        return run_crm_skill_command(
            name=args.name,
            repo_root=Path(args.repo_root).resolve(),
            username=args.user,
            roles=tuple(args.role),
            account_id=args.account_id,
            limit=args.limit,
        )

    parser.print_help()
    return 0


def _read_object_file(file_path: Path) -> Mapping[str, object]:
    data = read_yaml(file_path)
    if not isinstance(data, Mapping):
        raise ValueError(f"{file_path} must contain a YAML object")
    return data


def _object_from_data(data: Mapping[str, object]):
    object_type = str(data["object_type"])
    if object_type == "account":
        return _account_from_data(data)
    if object_type == "opportunity":
        return _opportunity_from_data(data)
    return _base_object_from_data(data)


def _base_kwargs(data: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "id": str(data["id"]),
        "object_type": str(data["object_type"]),
        "owner": str(data["owner"]),
        "created_by": str(data["created_by"]),
        "updated_by": str(data["updated_by"]),
        "created_at": _parse_utc_timestamp(str(data["created_at"])),
        "updated_at": _parse_utc_timestamp(str(data["updated_at"])),
        "version": int(data["version"]),
        "status": ObjectStatus(str(data["status"])),
        "visibility": ObjectVisibility(str(data["visibility"])),
        "links": _links_from_data(data),
        "tags": tuple(str(tag) for tag in data.get("tags", [])),
        "metadata": (
            data.get("metadata", {}) if isinstance(data.get("metadata", {}), Mapping) else {}
        ),
    }


def _base_object_from_data(data: Mapping[str, object]) -> BaseObject:
    return BaseObject(
        **_base_kwargs(data),
    )


def _account_from_data(data: Mapping[str, object]) -> CRMAccount:
    base = dict(_base_kwargs(data))
    base.pop("object_type")
    return CRMAccount(
        **base,
        name=str(data["name"]),
        stage=AccountStage(str(data["stage"])),
        industry=str(data["industry"]),
        arr=int(data["arr"]),
        health=CustomerHealth(str(data["health"])),
        renewal_date=str(data["renewal_date"]),
    )


def _opportunity_from_data(data: Mapping[str, object]) -> CRMOpportunity:
    base = dict(_base_kwargs(data))
    base.pop("object_type")
    return CRMOpportunity(
        **base,
        account_id=str(data["account_id"]),
        stage=OpportunityStage(str(data["stage"])),
        amount=int(data["amount"]),
        probability=float(data["probability"]),
        close_date=str(data["close_date"]),
        discount_requested=int(data["discount_requested"]),
        next_step=str(data["next_step"]),
        approval_status=ApprovalStatus(str(data["approval_status"])),
    )


def _links_from_data(data: Mapping[str, object]) -> tuple[ObjectLink, ...]:
    links = data.get("links", [])
    if not isinstance(links, list):
        return ()
    parsed = []
    for link in links:
        if isinstance(link, Mapping):
            parsed.append(
                ObjectLink(
                    target_type=str(link["target_type"]),
                    target_id=str(link["target_id"]),
                    relationship=str(link["relationship"]),
                )
            )
    return tuple(parsed)


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _read_before_state(
    store: LocalObjectStore, object_type: str, object_id: str
) -> Mapping[str, object]:
    try:
        return store.read_object(object_type, object_id).data
    except FileNotFoundError:
        return {}


def _demo_path_map() -> Mapping[str, str]:
    return {
        "account": "modules/crm/objects/accounts",
        "contact": "modules/crm/objects/contacts",
        "opportunity": "modules/crm/objects/opportunities",
        "defect": "modules/issues/objects/defects",
        "employee": "modules/hr/objects/employees",
    }


def _proposal_service(repo_root: Path) -> MutationProposalService:
    return MutationProposalService(
        repo_root=repo_root,
        object_store=LocalObjectStore(repo_root, path_map=_demo_path_map()),
        policy_engine=_demo_policy_engine(),
        domain_validators=(crm_lifecycle_validator,),
    )


def _github_approval_evidence(
    proposal,
    repo_root: Path,
    github_review_file: Optional[Path],
    approval_map_path: Path,
):
    if github_review_file is None:
        return None

    approval_map = read_github_approval_map(repo_root=repo_root, path=approval_map_path)
    return github_approval_evidence_from_pull_request_data(
        proposal=proposal,
        data=_read_structured_file(github_review_file),
        approval_map=approval_map,
    )


def _read_structured_file(path: Path):
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return read_yaml(path)


def _print_github_approval_evidence(approval_evidence) -> None:
    print("GitHub approvals:")
    print(f"- Satisfied: {_display_list(approval_evidence.satisfied_approvers)}")
    print(f"- Missing: {_display_list(approval_evidence.missing_approvers)}")


def _write_proposal_pr_report(
    report_file: Path,
    proposal,
    proposal_path: Path,
    result,
    approval_evidence,
) -> None:
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        render_proposal_pr_validation_report(
            proposal=proposal,
            result=result,
            proposal_path=proposal_path,
            approval_evidence=approval_evidence,
        ),
        encoding="utf-8",
    )


def _repo_display_path(repo_root: Path, path: Path) -> Path:
    try:
        return path.relative_to(repo_root)
    except ValueError:
        return path


def _display_list(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _preview_path(repo_root: Path, preview_dir: Path, proposal_id: str) -> Path:
    root = preview_dir
    if not root.is_absolute():
        root = repo_root / root
    return root / f"{proposal_id}.yaml"


def _issue_preview_path(repo_root: Path, preview_dir: Path, issue_number: int) -> Path:
    root = preview_dir
    if not root.is_absolute():
        root = repo_root / root
    return root / f"issue_{issue_number}.yaml"


def _read_issue_preview(repo_root: Path, preview_dir: Path, issue_number: int):
    path = _issue_preview_path(
        repo_root=repo_root,
        preview_dir=preview_dir,
        issue_number=issue_number,
    )
    return issue_from_data(read_yaml(path))


def _print_github_issue(issue) -> None:
    print(f"Issue: #{issue.number}")
    print(f"Title: {issue.title}")
    print(f"State: {issue.state}")
    print(f"URL: {issue.url}")
    if issue.labels:
        print(f"Labels: {_display_list(issue.labels)}")
    if issue.assignees:
        print(f"Assignees: {_display_list(issue.assignees)}")


def _schema_for_object_type(object_type: str):
    if object_type == "account":
        return account_schema()
    if object_type == "opportunity":
        return opportunity_schema()
    return base_object_schema(object_type=object_type)


def _demo_policy_engine() -> PolicyEngine:
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
            Permission(
                subject="sales_rep",
                action=PermissionAction.UPDATE,
                object_type="account",
                scope="owned_by_me",
                fields=("status", "tags", "metadata"),
            ),
        ),
    )
    rbac = RBACEngine(roles=(founder, sales_rep))
    return PolicyEngine(
        rbac=rbac,
        approval_rules=(
            approval_required(
                object_type="account",
                action=PermissionAction.UPDATE,
                fields=("metadata",),
                required_approvers=("sales_manager",),
                reason="Account metadata changes require sales manager approval in demo policy.",
                rule_id="account_metadata_approval",
            ),
        ),
    )
