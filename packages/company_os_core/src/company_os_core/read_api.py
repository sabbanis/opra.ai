"""Dependency-free local API surface."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from company_os_core.audit import AuditEventWriter
from company_os_core.crm import (
    AccountStage,
    ApprovalStatus,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    OpportunityStage,
    account_schema,
    crm_lifecycle_validator,
    opportunity_schema,
)
from company_os_core.crm_read_model import (
    CRMOpportunityReadRow,
    build_crm_read_model,
)
from company_os_core.crm_skills import run_crm_skill
from company_os_core.github import (
    DEFAULT_GITHUB_ISSUE_PREVIEW_DIR,
    DEFAULT_GITHUB_PR_PREVIEW_DIR,
    GitHubProposalPublisher,
    MockGitHubAdapter,
    ProposalPRValidator,
    issue_from_data,
    render_proposal_pr_validation_report,
)
from company_os_core.models import (
    BaseObject,
    ObjectLink,
    ObjectStatus,
    ObjectVisibility,
    PermissionAction,
    PolicyDecision,
    SourceInterface,
    User,
)
from company_os_core.mutation import GovernedMutationService
from company_os_core.object_store import LocalObjectStore
from company_os_core.policy import PolicyEngine
from company_os_core.proposals import (
    DEFAULT_MUTATION_PROPOSAL_DIR,
    MutationProposal,
    MutationProposalService,
)
from company_os_core.schema import base_object_schema, validate_object
from company_os_core.serialization import read_yaml, stable_hash, to_plain_data, write_yaml


@dataclass(frozen=True)
class APIResponse:
    """Response returned by the local API router."""

    status_code: int
    body: Mapping[str, Any] = field(default_factory=dict)


class LocalReadAPI:
    """Route local API requests to core services."""

    def __init__(self, repo_root: Path, policy_engine: PolicyEngine) -> None:
        self._repo_root = repo_root
        self._policy_engine = policy_engine

    def handle_get(
        self,
        path: str,
        query: Mapping[str, str],
        user: User,
    ) -> APIResponse:
        """Handle one dependency-free GET request."""

        try:
            return self._handle_get(path=path, query=query, user=user)
        except FileNotFoundError as exc:
            return APIResponse(status_code=404, body={"error": str(exc)})
        except ValueError as exc:
            return APIResponse(status_code=422, body={"error": str(exc)})
        except OSError as exc:
            return APIResponse(status_code=500, body={"error": str(exc)})

    def handle_post(
        self,
        path: str,
        body: Mapping[str, Any],
        user: User,
    ) -> APIResponse:
        """Handle one dependency-free POST request."""

        try:
            return self._handle_post(path=path, body=body, user=user)
        except FileNotFoundError as exc:
            return APIResponse(status_code=404, body={"error": str(exc)})
        except FileExistsError as exc:
            return APIResponse(status_code=409, body={"error": str(exc)})
        except ValueError as exc:
            return APIResponse(status_code=422, body={"error": str(exc)})
        except OSError as exc:
            return APIResponse(status_code=500, body={"error": str(exc)})

    def _handle_get(
        self,
        path: str,
        query: Mapping[str, str],
        user: User,
    ) -> APIResponse:
        if path == "/":
            return self._api_index()
        if path == "/health":
            return APIResponse(status_code=200, body={"status": "ok"})
        if path == "/objects":
            return self._objects(query)
        if path == "/object":
            return self._object(query)
        if path == "/proposals":
            return self._proposals()
        if path == "/audit/events":
            return self._audit_events()
        if path == "/github/previews/prs":
            return self._preview_files(DEFAULT_GITHUB_PR_PREVIEW_DIR, "pull_requests")
        if path == "/github/previews/issues":
            return self._preview_files(DEFAULT_GITHUB_ISSUE_PREVIEW_DIR, "issues")
        if path == "/crm/summary":
            return self._crm_summary(user)
        if path == "/crm/accounts":
            return self._crm_accounts(user)
        if path == "/crm/opportunities":
            return self._crm_opportunities(user=user, query=query)
        if path.startswith("/crm/skills/"):
            return self._crm_skill(path=path, query=query, user=user)
        return APIResponse(status_code=404, body={"error": f"Unknown API route: {path}"})

    def _handle_post(
        self,
        path: str,
        body: Mapping[str, Any],
        user: User,
    ) -> APIResponse:
        if path == "/objects/validate":
            return self._validate_object_payload(body)
        if path == "/objects/policy-check":
            return self._policy_check(body=body, user=user)
        if path == "/objects/governed-write":
            return self._governed_write(body=body, user=user)
        if path == "/proposals":
            return self._create_proposal(body=body, user=user)
        if path == "/github/issues":
            return self._create_issue_preview(body)

        parts = tuple(part for part in path.strip("/").split("/") if part)
        if len(parts) == 3 and parts[0] == "proposals":
            proposal_id, operation = parts[1], parts[2]
            if operation == "approve":
                return self._approve_proposal(proposal_id, body=body, user=user)
            if operation == "reject":
                return self._reject_proposal(proposal_id, body=body, user=user)
            if operation == "apply":
                return self._apply_proposal(proposal_id, user=user)
            if operation == "publish-pr":
                return self._publish_pr_preview(proposal_id, body=body)
            if operation == "validate-pr":
                return self._validate_proposal_pr(proposal_id)
        if len(parts) == 3 and parts[0] == "github" and parts[1] == "issues":
            return self._update_issue_preview(issue_number=int(parts[2]), body=body)

        return APIResponse(status_code=404, body={"error": f"Unknown API route: {path}"})

    def _api_index(self) -> APIResponse:
        return APIResponse(
            status_code=200,
            body={
                "name": "opra.ai API",
                "status": "ok",
                "endpoints": [
                    "/health",
                    "/objects",
                    "/object",
                    "/objects/validate",
                    "/objects/policy-check",
                    "/objects/governed-write",
                    "/proposals",
                    "/audit/events",
                    "/github/issues",
                    "/github/previews/prs",
                    "/github/previews/issues",
                    "/crm/summary",
                    "/crm/accounts",
                    "/crm/opportunities",
                    "/crm/skills/pipeline-summary",
                    "/crm/skills/renewal-health",
                    "/crm/skills/opportunity-view",
                ],
            },
        )

    def _crm_summary(self, user: User) -> APIResponse:
        authorization = self._authorize_reads(user, ("account", "opportunity"))
        if authorization is not None:
            return authorization

        read_model = build_crm_read_model(self._repo_root)
        return APIResponse(
            status_code=200,
            body={
                "generated_at": to_plain_data(read_model.generated_at),
                "summary": to_plain_data(read_model.summary),
            },
        )

    def _crm_accounts(self, user: User) -> APIResponse:
        authorization = self._authorize_reads(user, ("account",))
        if authorization is not None:
            return authorization

        read_model = build_crm_read_model(self._repo_root)
        return APIResponse(
            status_code=200,
            body={"accounts": to_plain_data(read_model.accounts)},
        )

    def _crm_opportunities(self, user: User, query: Mapping[str, str]) -> APIResponse:
        authorization = self._authorize_reads(user, ("account", "opportunity"))
        if authorization is not None:
            return authorization

        read_model = build_crm_read_model(self._repo_root)
        account_id = query.get("account_id", "")
        opportunities = read_model.opportunities
        if account_id:
            opportunities = tuple(
                opportunity
                for opportunity in opportunities
                if opportunity.account_id == account_id
            )
        return APIResponse(
            status_code=200,
            body={"opportunities": to_plain_data(_limit_rows(opportunities, query))},
        )

    def _crm_skill(self, path: str, query: Mapping[str, str], user: User) -> APIResponse:
        name = path.removeprefix("/crm/skills/").strip("/")
        if not name:
            return APIResponse(status_code=404, body={"error": "CRM Skill name is required."})

        result = run_crm_skill(
            name=name,
            repo_root=self._repo_root,
            user=user,
            policy_engine=self._policy_engine,
            inputs=query,
        )
        status_code = 200 if result.allowed else 403
        if result.reasons == ("Unknown CRM Skill.",):
            status_code = 404
        return APIResponse(
            status_code=status_code,
            body={
                "name": result.name,
                "decision": result.decision.value,
                "summary": result.summary,
                "data": to_plain_data(result.data),
                "reasons": list(result.reasons),
            },
        )

    def _objects(self, query: Mapping[str, str]) -> APIResponse:
        requested_type = query.get("object_type", "")
        rows = []
        for object_type, directory in _demo_path_map().items():
            if requested_type and object_type != requested_type:
                continue
            root = self._repo_root / directory
            if not root.exists():
                continue
            for path in sorted(root.glob("*.yaml")):
                data = _read_mapping(path)
                rows.append(self._object_row(path=path, data=data))
        return APIResponse(status_code=200, body={"objects": rows})

    def _object(self, query: Mapping[str, str]) -> APIResponse:
        path = self._safe_repo_path(query.get("path", ""))
        data = _read_mapping(path)
        return APIResponse(
            status_code=200,
            body={
                "path": self._display_path(path),
                "hash": stable_hash(data),
                "object": data,
            },
        )

    def _validate_object_payload(self, body: Mapping[str, Any]) -> APIResponse:
        data, path = self._object_data_from_body(body)
        object_type = str(data.get("object_type", ""))
        result = validate_object(data, _schema_for_object_type(object_type))
        return APIResponse(
            status_code=200,
            body={
                "valid": result.valid,
                "path": self._display_path(path) if path is not None else "",
                "hash": stable_hash(data),
                "object_type": object_type,
                "object_id": str(data.get("id", "")),
                "issues": _validation_issues(result.issues),
            },
        )

    def _policy_check(self, body: Mapping[str, Any], user: User) -> APIResponse:
        data, path = self._object_data_from_body(body)
        action = PermissionAction(str(body.get("action", PermissionAction.READ.value)))
        fields = _string_tuple(body.get("fields", []))
        result = self._policy_engine.evaluate(
            user=user,
            action=action,
            obj=data,
            fields=fields,
        )
        return APIResponse(
            status_code=200,
            body={
                "decision": result.decision.value,
                "path": self._display_path(path) if path is not None else "",
                "object_type": str(data.get("object_type", "")),
                "object_id": str(data.get("id", "")),
                "reasons": list(result.reasons),
                "required_approvers": list(result.required_approvers),
                "matched_permissions": list(result.matched_permissions),
            },
        )

    def _governed_write(self, body: Mapping[str, Any], user: User) -> APIResponse:
        data, _ = self._object_data_from_body(body)
        obj = _object_from_data(data)
        action = PermissionAction(str(body.get("action", PermissionAction.UPDATE.value)))
        fields = _string_tuple(body.get("fields", []))
        request_id = _required_text("request_id", str(body.get("request_id", "")))
        store = self._object_store()
        service = GovernedMutationService(
            object_store=store,
            policy_engine=self._policy_engine,
            audit_writer=AuditEventWriter(self._event_dir()),
            domain_validators=(crm_lifecycle_validator,),
        )
        if action == PermissionAction.CREATE:
            result = service.create_object(
                user=user,
                obj=obj,
                schema=_schema_for_object_type(obj.object_type),
                request_id=request_id,
                source_interface=SourceInterface.WEB,
            )
        elif action == PermissionAction.UPDATE:
            before = store.read_object(obj.object_type, obj.id).data
            result = service.update_object(
                user=user,
                before=before,
                after=obj,
                schema=_schema_for_object_type(obj.object_type),
                fields=fields,
                request_id=request_id,
                source_interface=SourceInterface.WEB,
            )
        else:
            raise ValueError("governed-write supports create and update actions only")

        body_payload: dict[str, Any] = {
            "decision": result.policy_result.decision.value,
            "committed": result.committed,
            "validation": {
                "valid": result.validation_result.valid,
                "issues": _validation_issues(result.validation_result.issues),
            },
            "reasons": list(result.policy_result.reasons),
            "required_approvers": list(result.policy_result.required_approvers),
            "audit_event": self._display_path(result.audit_event.path),
        }
        if result.stored_object is not None:
            body_payload["stored_object"] = self._display_path(result.stored_object.path)
            body_payload["hash"] = result.stored_object.content_hash
        return APIResponse(status_code=200, body=body_payload)

    def _proposals(self) -> APIResponse:
        proposals = []
        for path in sorted(self._proposal_dir().glob("*.yaml"), reverse=True):
            proposal = self._proposal_service().read_proposal(path)
            proposals.append(self._proposal_payload(path=path, proposal=proposal))
        return APIResponse(status_code=200, body={"proposals": proposals})

    def _create_proposal(self, body: Mapping[str, Any], user: User) -> APIResponse:
        data, _ = self._object_data_from_body(body)
        obj = _object_from_data(data)
        action = PermissionAction(str(body.get("action", PermissionAction.UPDATE.value)))
        request_id = _required_text("request_id", str(body.get("request_id", "")))
        fields = _string_tuple(body.get("fields", []))
        before = None
        if action == PermissionAction.UPDATE:
            before = self._object_store().read_object(obj.object_type, obj.id).data
        elif action != PermissionAction.CREATE:
            raise ValueError("proposals support create and update actions only")

        written = self._proposal_service().propose(
            user=user,
            action=action,
            before=before,
            after=obj,
            schema=_schema_for_object_type(obj.object_type),
            fields=fields,
            request_id=request_id,
            source_interface=SourceInterface.WEB,
        )
        return APIResponse(
            status_code=201,
            body=self._proposal_payload(path=written.path, proposal=written.proposal),
        )

    def _approve_proposal(
        self,
        proposal_id: str,
        body: Mapping[str, Any],
        user: User,
    ) -> APIResponse:
        path = self._proposal_path(proposal_id)
        written = self._proposal_service().approve(
            path=path,
            user=user,
            reason=str(body.get("reason", "")),
        )
        return APIResponse(
            status_code=200,
            body=self._proposal_payload(path=written.path, proposal=written.proposal),
        )

    def _reject_proposal(
        self,
        proposal_id: str,
        body: Mapping[str, Any],
        user: User,
    ) -> APIResponse:
        path = self._proposal_path(proposal_id)
        written = self._proposal_service().reject(
            path=path,
            user=user,
            reason=str(body.get("reason", "")),
        )
        return APIResponse(
            status_code=200,
            body=self._proposal_payload(path=written.path, proposal=written.proposal),
        )

    def _apply_proposal(self, proposal_id: str, user: User) -> APIResponse:
        path = self._proposal_path(proposal_id)
        proposal = self._proposal_service().read_proposal(path)
        applied = self._proposal_service().apply(
            path=path,
            user=user,
            schema=_schema_for_object_type(proposal.object_type),
            audit_writer=AuditEventWriter(self._event_dir()),
            source_interface=SourceInterface.WEB,
        )
        return APIResponse(
            status_code=200,
            body={
                **self._proposal_payload(
                    path=applied.proposal_path,
                    proposal=applied.proposal,
                ),
                "target_path": self._display_path(applied.target_path),
                "audit_event": self._display_path(applied.audit_event.path),
            },
        )

    def _publish_pr_preview(
        self,
        proposal_id: str,
        body: Mapping[str, Any],
    ) -> APIResponse:
        proposal_path = self._proposal_path(proposal_id)
        proposal = self._proposal_service().read_proposal(proposal_path)
        publisher = GitHubProposalPublisher(
            adapter=MockGitHubAdapter(
                repo_url=str(body.get("repo_url", "https://github.com/local/opra.ai"))
            ),
            repo_root=self._repo_root,
        )
        published = publisher.publish(
            proposal=proposal,
            proposal_path=proposal_path,
            base_branch=str(body.get("base_branch", "main")),
        )
        preview_path = self._preview_path(DEFAULT_GITHUB_PR_PREVIEW_DIR, proposal.id)
        write_yaml(preview_path, published)
        return APIResponse(
            status_code=201,
            body={
                "preview_path": self._display_path(preview_path),
                "published": to_plain_data(published),
            },
        )

    def _validate_proposal_pr(self, proposal_id: str) -> APIResponse:
        proposal_path = self._proposal_path(proposal_id)
        proposal = self._proposal_service().read_proposal(proposal_path)
        result = ProposalPRValidator(repo_root=self._repo_root).validate(
            proposal=proposal,
            proposal_path=proposal_path,
        )
        report = render_proposal_pr_validation_report(
            proposal=proposal,
            result=result,
            proposal_path=Path(self._display_path(proposal_path)),
        )
        return APIResponse(
            status_code=200,
            body={
                "valid": result.valid,
                "issues": _validation_issues(result.issues),
                "report": report,
            },
        )

    def _audit_events(self) -> APIResponse:
        events = []
        root = self._event_dir()
        if root.exists():
            for path in sorted(root.glob("*.yaml"), reverse=True):
                events.append(
                    {
                        "path": self._display_path(path),
                        "event": _read_mapping(path),
                    }
                )
        return APIResponse(status_code=200, body={"events": events})

    def _preview_files(self, directory: Path, key: str) -> APIResponse:
        previews = []
        root = directory if directory.is_absolute() else self._repo_root / directory
        if root.exists():
            for path in sorted(root.glob("*.yaml"), reverse=True):
                previews.append(
                    {
                        "path": self._display_path(path),
                        "preview": _read_mapping(path),
                    }
                )
        return APIResponse(status_code=200, body={key: previews})

    def _create_issue_preview(self, body: Mapping[str, Any]) -> APIResponse:
        adapter = self._issue_preview_adapter(body)
        issue = adapter.create_issue(
            title=str(body.get("title", "")),
            body=str(body.get("body", "")),
            labels=_string_tuple(body.get("labels", [])),
            assignees=_string_tuple(body.get("assignees", [])),
        )
        preview_path = self._issue_preview_path(issue.number)
        write_yaml(preview_path, issue)
        return APIResponse(
            status_code=201,
            body={
                "preview_path": self._display_path(preview_path),
                "issue": to_plain_data(issue),
            },
        )

    def _update_issue_preview(
        self,
        issue_number: int,
        body: Mapping[str, Any],
    ) -> APIResponse:
        adapter = self._issue_preview_adapter(body)
        issue = adapter.update_issue(
            number=issue_number,
            title=_optional_text(body.get("title")),
            body=_optional_text(body.get("body")),
            state=_optional_text(body.get("state")),
            labels=_string_tuple(body.get("labels", [])),
            assignees=_string_tuple(body.get("assignees", [])),
        )
        preview_path = self._issue_preview_path(issue.number)
        write_yaml(preview_path, issue)
        return APIResponse(
            status_code=200,
            body={
                "preview_path": self._display_path(preview_path),
                "issue": to_plain_data(issue),
            },
        )

    def _authorize_reads(
        self,
        user: User,
        object_types: tuple[str, ...],
    ) -> Optional[APIResponse]:
        for object_type in object_types:
            result = self._policy_engine.evaluate(
                user=user,
                action=PermissionAction.READ,
                obj={
                    "id": f"{object_type}_read_model",
                    "object_type": object_type,
                    "owner": "",
                },
            )
            if result.decision != PolicyDecision.ALLOW:
                return APIResponse(
                    status_code=403,
                    body={
                        "error": "Read request denied by policy.",
                        "object_type": object_type,
                        "reasons": list(result.reasons),
                    },
                )
        return None

    def _object_data_from_body(
        self,
        body: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], Optional[Path]]:
        if "object" in body:
            value = body["object"]
            if not isinstance(value, Mapping):
                raise ValueError("object must be a JSON object")
            return value, None

        path_value = str(body.get("path", ""))
        if not path_value:
            raise ValueError("object or path is required")
        path = self._safe_repo_path(path_value)
        return _read_mapping(path), path

    def _object_row(self, path: Path, data: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "path": self._display_path(path),
            "hash": stable_hash(data),
            "id": str(data.get("id", "")),
            "object_type": str(data.get("object_type", "")),
            "name": str(data.get("name", data.get("id", ""))),
            "owner": str(data.get("owner", "")),
            "status": str(data.get("status", "")),
            "version": data.get("version", ""),
            "data": data,
        }

    def _proposal_payload(
        self,
        path: Path,
        proposal: MutationProposal,
    ) -> Mapping[str, Any]:
        remaining = self._proposal_service().remaining_approvers(proposal)
        return {
            "path": self._display_path(path),
            "remaining_approvers": list(remaining),
            "proposal": to_plain_data(proposal),
        }

    def _object_store(self) -> LocalObjectStore:
        return LocalObjectStore(self._repo_root, path_map=_demo_path_map())

    def _proposal_service(self) -> MutationProposalService:
        return MutationProposalService(
            repo_root=self._repo_root,
            object_store=self._object_store(),
            policy_engine=self._policy_engine,
            domain_validators=(crm_lifecycle_validator,),
        )

    def _proposal_dir(self) -> Path:
        return self._repo_root / DEFAULT_MUTATION_PROPOSAL_DIR

    def _proposal_path(self, proposal_id: str) -> Path:
        proposal_id = _safe_file_stem(proposal_id)
        path = self._proposal_dir() / f"{proposal_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Proposal not found: {proposal_id}")
        return path

    def _event_dir(self) -> Path:
        return self._repo_root / "platform/audit/events"

    def _preview_path(self, directory: Path, stem: str) -> Path:
        return self._repo_root / directory / f"{_safe_file_stem(stem)}.yaml"

    def _issue_preview_path(self, issue_number: int) -> Path:
        if issue_number < 1:
            raise ValueError("issue number must be positive")
        return self._repo_root / DEFAULT_GITHUB_ISSUE_PREVIEW_DIR / f"issue_{issue_number}.yaml"

    def _issue_preview_adapter(self, body: Mapping[str, Any]) -> MockGitHubAdapter:
        adapter = MockGitHubAdapter(
            repo_url=str(body.get("repo_url", "https://github.com/local/opra.ai"))
        )
        root = self._repo_root / DEFAULT_GITHUB_ISSUE_PREVIEW_DIR
        if root.exists():
            for path in sorted(root.glob("issue_*.yaml")):
                adapter.seed_issue(issue_from_data(read_yaml(path)))
        return adapter

    def _safe_repo_path(self, value: str) -> Path:
        if not value or not value.strip():
            raise ValueError("path is required")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self._repo_root / candidate
        try:
            candidate.resolve().relative_to(self._repo_root.resolve())
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {value}") from exc
        return candidate

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._repo_root))
        except ValueError:
            return str(path)


def _limit_rows(
    rows: tuple[CRMOpportunityReadRow, ...],
    query: Mapping[str, str],
) -> tuple[CRMOpportunityReadRow, ...]:
    limit = _positive_int(query.get("limit"), default=len(rows))
    return rows[:limit]


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _read_mapping(path: Path) -> Mapping[str, Any]:
    data = read_yaml(path)
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} must contain a YAML object")
    return data


def _schema_for_object_type(object_type: str):
    if object_type == "account":
        return account_schema()
    if object_type == "opportunity":
        return opportunity_schema()
    return base_object_schema(object_type=object_type)


def _object_from_data(data: Mapping[str, Any]):
    object_type = str(data["object_type"])
    if object_type == "account":
        return _account_from_data(data)
    if object_type == "opportunity":
        return _opportunity_from_data(data)
    return _base_object_from_data(data)


def _base_kwargs(data: Mapping[str, Any]) -> Mapping[str, Any]:
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
        "metadata": _mapping_or_empty(data.get("metadata", {})),
    }


def _base_object_from_data(data: Mapping[str, Any]) -> BaseObject:
    return BaseObject(**_base_kwargs(data))


def _account_from_data(data: Mapping[str, Any]) -> CRMAccount:
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


def _opportunity_from_data(data: Mapping[str, Any]) -> CRMOpportunity:
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


def _links_from_data(data: Mapping[str, Any]) -> tuple[ObjectLink, ...]:
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


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _demo_path_map() -> Mapping[str, str]:
    return {
        "account": "modules/crm/objects/accounts",
        "contact": "modules/crm/objects/contacts",
        "opportunity": "modules/crm/objects/opportunities",
        "defect": "modules/issues/objects/defects",
        "employee": "modules/hr/objects/employees",
    }


def _validation_issues(issues) -> list[Mapping[str, str]]:
    return [
        {
            "field": str(issue.field),
            "message": str(issue.message),
        }
        for issue in issues
    ]


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == {}:
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError("expected a list of strings")


def _required_text(field_name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def _optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _safe_file_stem(value: str) -> str:
    if not re.match(r"^[A-Za-z0-9_.-]+$", value or ""):
        raise ValueError(f"invalid file id: {value}")
    return value
