"""CRM dashboard read-model indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from company_os_core.crm import (
    CustomerHealth,
    OpportunityStage,
    account_schema,
    opportunity_schema,
)
from company_os_core.schema import ObjectSchema, ValidationIssue, validate_object
from company_os_core.serialization import read_yaml, to_json


DEFAULT_CRM_READ_MODEL_PATH = Path("platform/dashboards/read_models/crm_summary.json")

OPEN_OPPORTUNITY_STAGES = {
    OpportunityStage.LEAD.value,
    OpportunityStage.QUALIFIED.value,
    OpportunityStage.DISCOVERY.value,
    OpportunityStage.PROPOSAL.value,
    OpportunityStage.NEGOTIATION.value,
    OpportunityStage.RENEWAL_DUE.value,
    OpportunityStage.RENEWAL_PROPOSAL.value,
}


@dataclass(frozen=True)
class CRMAccountReadRow:
    """Dashboard row for one CRM account."""

    id: str
    name: str
    owner: str
    stage: str
    health: str
    arr: int
    renewal_date: str
    open_opportunity_count: int
    open_pipeline_amount: int
    weighted_pipeline_amount: int
    next_close_date: str = ""


@dataclass(frozen=True)
class CRMOpportunityReadRow:
    """Dashboard row for one CRM opportunity."""

    id: str
    account_id: str
    account_name: str
    owner: str
    stage: str
    amount: int
    probability: float
    weighted_amount: int
    close_date: str
    discount_requested: int
    approval_status: str
    next_step: str


@dataclass(frozen=True)
class CRMReadModelSummary:
    """Aggregate values for the CRM dashboard."""

    account_count: int
    opportunity_count: int
    total_arr: int
    open_pipeline_amount: int
    weighted_pipeline_amount: int
    renewal_account_count: int
    at_risk_account_count: int


@dataclass(frozen=True)
class CRMReadModel:
    """CRM dashboard read model."""

    generated_at: datetime
    summary: CRMReadModelSummary
    accounts: tuple[CRMAccountReadRow, ...] = field(default_factory=tuple)
    opportunities: tuple[CRMOpportunityReadRow, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WrittenCRMReadModel:
    """Written CRM read-model artifact."""

    path: Path
    read_model: CRMReadModel


class ReadModelBuildError(ValueError):
    """Raised when source objects cannot be indexed into a read model."""

    def __init__(self, path: Path, issues: tuple[ValidationIssue, ...]) -> None:
        self.path = path
        self.issues = issues
        messages = "; ".join(f"{issue.field}: {issue.message}" for issue in issues)
        super().__init__(f"{path}: {messages}")


def build_crm_read_model(
    repo_root: Path,
    generated_at: Optional[datetime] = None,
) -> CRMReadModel:
    """Build the CRM dashboard read model from source-of-truth YAML files."""

    account_records = _load_source_records(
        repo_root / "modules/crm/objects/accounts",
        account_schema(),
    )
    opportunity_records = _load_source_records(
        repo_root / "modules/crm/objects/opportunities",
        opportunity_schema(),
    )
    account_names = {str(account["id"]): str(account["name"]) for account in account_records}
    opportunity_rows = tuple(
        _opportunity_row(opportunity, account_names) for opportunity in opportunity_records
    )
    opportunities_by_account = _group_open_opportunities_by_account(opportunity_rows)
    account_rows = tuple(
        _account_row(account, opportunities_by_account) for account in account_records
    )

    summary = CRMReadModelSummary(
        account_count=len(account_rows),
        opportunity_count=len(opportunity_rows),
        total_arr=sum(account.arr for account in account_rows),
        open_pipeline_amount=sum(account.open_pipeline_amount for account in account_rows),
        weighted_pipeline_amount=sum(account.weighted_pipeline_amount for account in account_rows),
        renewal_account_count=sum(
            1 for account in account_rows if account.stage in ("renewal_due", "renewal_proposal")
        ),
        at_risk_account_count=sum(
            1
            for account in account_rows
            if account.health in (CustomerHealth.YELLOW.value, CustomerHealth.RED.value)
        ),
    )
    return CRMReadModel(
        generated_at=generated_at or datetime.now(timezone.utc),
        summary=summary,
        accounts=account_rows,
        opportunities=opportunity_rows,
    )


def write_crm_read_model(
    repo_root: Path,
    output_path: Optional[Path] = None,
    generated_at: Optional[datetime] = None,
) -> WrittenCRMReadModel:
    """Build and write the CRM dashboard read model as JSON."""

    read_model = build_crm_read_model(repo_root, generated_at=generated_at)
    target_path = output_path or repo_root / DEFAULT_CRM_READ_MODEL_PATH
    if not target_path.is_absolute():
        target_path = repo_root / target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(to_json(read_model) + "\n", encoding="utf-8")
    return WrittenCRMReadModel(path=target_path, read_model=read_model)


def _load_source_records(directory: Path, schema: ObjectSchema) -> tuple[Mapping[str, Any], ...]:
    if not directory.exists():
        return ()

    records = []
    for path in sorted(directory.glob("*.yaml")):
        data = read_yaml(path)
        if not isinstance(data, Mapping):
            raise ReadModelBuildError(
                path,
                (ValidationIssue(field="<root>", message="source file must contain an object"),),
            )

        result = validate_object(data, schema)
        if not result.valid:
            raise ReadModelBuildError(path, result.issues)

        records.append(data)
    return tuple(records)


def _opportunity_row(
    opportunity: Mapping[str, Any],
    account_names: Mapping[str, str],
) -> CRMOpportunityReadRow:
    amount = int(opportunity["amount"])
    probability = float(opportunity["probability"])
    account_id = str(opportunity["account_id"])
    return CRMOpportunityReadRow(
        id=str(opportunity["id"]),
        account_id=account_id,
        account_name=account_names.get(account_id, ""),
        owner=str(opportunity["owner"]),
        stage=str(opportunity["stage"]),
        amount=amount,
        probability=probability,
        weighted_amount=round(amount * probability),
        close_date=str(opportunity["close_date"]),
        discount_requested=int(opportunity["discount_requested"]),
        approval_status=str(opportunity["approval_status"]),
        next_step=str(opportunity["next_step"]),
    )


def _account_row(
    account: Mapping[str, Any],
    opportunities_by_account: Mapping[str, tuple[CRMOpportunityReadRow, ...]],
) -> CRMAccountReadRow:
    account_opportunities = opportunities_by_account.get(str(account["id"]), ())
    close_dates = sorted(
        opportunity.close_date for opportunity in account_opportunities if opportunity.close_date
    )
    return CRMAccountReadRow(
        id=str(account["id"]),
        name=str(account["name"]),
        owner=str(account["owner"]),
        stage=str(account["stage"]),
        health=str(account["health"]),
        arr=int(account["arr"]),
        renewal_date=str(account["renewal_date"]),
        open_opportunity_count=len(account_opportunities),
        open_pipeline_amount=sum(opportunity.amount for opportunity in account_opportunities),
        weighted_pipeline_amount=sum(
            opportunity.weighted_amount for opportunity in account_opportunities
        ),
        next_close_date=close_dates[0] if close_dates else "",
    )


def _group_open_opportunities_by_account(
    opportunities: tuple[CRMOpportunityReadRow, ...],
) -> Mapping[str, tuple[CRMOpportunityReadRow, ...]]:
    grouped: dict[str, list[CRMOpportunityReadRow]] = {}
    for opportunity in opportunities:
        if opportunity.stage not in OPEN_OPPORTUNITY_STAGES:
            continue
        grouped.setdefault(opportunity.account_id, []).append(opportunity)
    return {
        account_id: tuple(sorted(rows, key=lambda row: (row.close_date, row.id)))
        for account_id, rows in grouped.items()
    }
