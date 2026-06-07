"""Dependency-free local read API surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from company_os_core.crm_read_model import (
    CRMOpportunityReadRow,
    build_crm_read_model,
)
from company_os_core.crm_skills import run_crm_skill
from company_os_core.models import PermissionAction, PolicyDecision, User
from company_os_core.policy import PolicyEngine
from company_os_core.serialization import to_plain_data


@dataclass(frozen=True)
class APIResponse:
    """Response returned by the local read API router."""

    status_code: int
    body: Mapping[str, Any] = field(default_factory=dict)


class LocalReadAPI:
    """Route local read API requests to core services."""

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
        except ValueError as exc:
            return APIResponse(status_code=422, body={"error": str(exc)})

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
        if path == "/crm/summary":
            return self._crm_summary(user)
        if path == "/crm/accounts":
            return self._crm_accounts(user)
        if path == "/crm/opportunities":
            return self._crm_opportunities(user=user, query=query)
        if path.startswith("/crm/skills/"):
            return self._crm_skill(path=path, query=query, user=user)
        return APIResponse(status_code=404, body={"error": f"Unknown API route: {path}"})

    def _api_index(self) -> APIResponse:
        return APIResponse(
            status_code=200,
            body={
                "name": "opra.ai API",
                "status": "ok",
                "endpoints": [
                    "/health",
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
