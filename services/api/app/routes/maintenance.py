from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, get_maintenance_service
from app.errors import AppError
from app.maintenance.taxonomy import catalog
from app.models.user import User
from app.services.maintenance import (
    InvalidMaintenance,
    MaintenanceNotFound,
    MaintenanceService,
)

router = APIRouter(prefix="/v1/maintenance", tags=["maintenance"])


class CreateMaintenanceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bike_id: UUID
    service_date: date
    system: str
    component: str
    action: str
    reason: str
    performer_type: str
    evidence_type: str = "owner_reported"
    component_detail: str | None = None
    engine_hours: Decimal | None = None
    engine_hours_is_estimated: bool = True
    service_type: str | None = None
    reason_details: str | None = None
    performer_name: str | None = None
    parts: str | None = None
    fluids: str | None = None
    cost: Decimal | None = None
    source: str | None = None
    linked_conversation_id: UUID | None = None
    details: str | None = None


class UpdateMaintenanceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_date: date | None = None
    system: str | None = None
    component: str | None = None
    component_detail: str | None = None
    action: str | None = None
    reason: str | None = None
    performer_type: str | None = None
    evidence_type: str | None = None
    engine_hours: Decimal | None = None
    engine_hours_is_estimated: bool | None = None
    service_type: str | None = None
    reason_details: str | None = None
    performer_name: str | None = None
    parts: str | None = None
    fluids: str | None = None
    cost: Decimal | None = None
    source: str | None = None
    linked_conversation_id: UUID | None = None
    details: str | None = None


class MaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bike_id: UUID
    service_date: date
    engine_hours: Decimal | None
    engine_hours_is_estimated: bool
    system: str
    component: str
    component_detail: str | None
    action: str
    service_type: str | None
    reason: str
    reason_details: str | None
    performer_type: str
    performer_name: str | None
    parts: str | None
    fluids: str | None
    cost: Decimal | None
    evidence_type: str
    source: str | None
    linked_conversation_id: UUID | None
    details: str | None
    created_at: datetime
    updated_at: datetime


def _raise(exc: Exception) -> NoReturn:
    if isinstance(exc, MaintenanceNotFound):
        raise AppError("not_found", str(exc), status_code=404) from exc
    if isinstance(exc, InvalidMaintenance):
        raise AppError("invalid_maintenance", str(exc), status_code=400) from exc
    raise exc


@router.get("/taxonomy")
def get_taxonomy(_user: Annotated[User, Depends(get_current_user)]):
    return catalog()


class CreateRuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bike_id: UUID
    system: str
    component: str
    action: str
    initial_interval_hours: Decimal | None = None
    recurring_interval_hours: Decimal | None = None
    calendar_interval_days: int | None = None
    whichever_comes_first: bool = True
    usage_condition_variant: str = "standard"


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bike_id: UUID
    system: str
    component: str
    action: str
    initial_interval_hours: Decimal | None
    recurring_interval_hours: Decimal | None
    calendar_interval_days: int | None
    whichever_comes_first: bool
    usage_condition_variant: str
    validation_status: str
    rule_version: int
    pipeline_version: str | None = None
    active: bool
    supersedes_rule_id: UUID | None = None
    source_document_id: UUID | None = None
    source_page: int | None = None
    source_span: str | None = None
    extraction_confidence: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class ExtractRulesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bike_id: UUID
    document_id: UUID | None = None
    force: bool = False
    # Test/dev hooks — production UI uses document_id / primary manual only.
    passages: list[dict] | None = None
    proposals: list[dict] | None = None
    activate: bool = True


@router.get("/due-state")
def get_due_state(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
    bike_id: UUID = Query(...),
):
    try:
        items = service.due_state(user, bike_id)
    except MaintenanceNotFound as exc:
        _raise(exc)
    return [item.as_dict() for item in items]


@router.get("/recommendations")
def get_recommendations(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
    bike_id: UUID = Query(...),
    context_tags: str | None = Query(
        None,
        description=(
            "Comma-separated: dust,sand,mud,wet,race,upcoming_ride,"
            "modification,symptom"
        ),
    ),
    include_ai: bool = Query(False),
):
    """Deterministic baseline + optional contextual advice. Intervals are never rewritten."""
    tags = [part.strip() for part in (context_tags or "").split(",") if part.strip()]
    try:
        bundle = service.recommendations(
            user, bike_id, context_tags=tags, include_ai=include_ai
        )
    except MaintenanceNotFound as exc:
        _raise(exc)
    return bundle.as_dict()


@router.get("/rules")
def list_rules(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
    bike_id: UUID = Query(...),
    include_inactive: bool = Query(False),
):
    try:
        rows = service.list_rules(user, bike_id, include_inactive=include_inactive)
    except MaintenanceNotFound as exc:
        _raise(exc)
    return [RuleResponse.model_validate(row) for row in rows]


@router.post("/rules", status_code=201)
def create_rule(
    body: CreateRuleBody,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        row = service.create_rule(user, **body.model_dump())
    except (MaintenanceNotFound, InvalidMaintenance) as exc:
        _raise(exc)
    return RuleResponse.model_validate(row)


@router.post("/rules/extract")
def extract_rules(
    body: ExtractRulesBody,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
    session: Annotated[Session, Depends(get_db)],
):
    """Build or rebuild the maintenance plan from the bike's manufacturer manual."""
    try:
        if body.proposals is not None:
            source_text = None
            if body.passages:
                source_text = "\n".join(
                    str(p.get("text") or "")
                    for p in body.passages
                    if isinstance(p, dict)
                )
            result = service.accept_proposals(
                user,
                bike_id=body.bike_id,
                proposals=body.proposals,
                source_text=source_text,
                document_id=body.document_id,
                activate=body.activate,
            )
        elif body.passages is not None:
            passages = _passages_from_body(body)
            from vroometr.ai.factory import get_chat_model

            result = service.extract_from_passages(
                user,
                bike_id=body.bike_id,
                passages=passages,
                chat=get_chat_model(),
                document_id=body.document_id,
                activate=body.activate,
            )
        else:
            document_id, pages = _manual_pages(user, body.bike_id, body.document_id, session)
            from vroometr.ai.factory import get_chat_model

            result = service.extract_from_document(
                user,
                bike_id=body.bike_id,
                document_id=document_id,
                pages=pages,
                chat=get_chat_model(),
                activate=True,
                force=body.force,
            )
    except (MaintenanceNotFound, InvalidMaintenance) as exc:
        _raise(exc)
    return {
        "pipeline_version": result["pipeline_version"],
        "accepted": [RuleResponse.model_validate(row) for row in result["accepted"]],
        "rejected": result["rejected"],
        "skipped": bool(result.get("skipped")),
        "reason": result.get("reason"),
    }


@router.post("/rules/{rule_id}/activate")
def activate_rule(
    rule_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        row = service.activate_rule(user, rule_id)
    except (MaintenanceNotFound, InvalidMaintenance) as exc:
        _raise(exc)
    return RuleResponse.model_validate(row)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        service.delete_rule(user, rule_id)
    except MaintenanceNotFound as exc:
        _raise(exc)


def _passages_from_body(body: ExtractRulesBody):
    from app.maintenance.rule_extraction import SourcePassage

    out = []
    for item in body.passages or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        page = int(item.get("page") or 1)
        doc_id = str(body.document_id) if body.document_id else None
        out.append(SourcePassage(page=page, text=text, document_id=doc_id))
    if not out:
        raise InvalidMaintenance("Passages are empty.")
    return out


def _manual_pages(
    user: User, bike_id: UUID, document_id: UUID | None, session: Session
):
    from app.repositories.document_ingestion import DocumentIngestionRepository
    from app.repositories.documents import DocumentRepository

    docs = DocumentRepository(session)
    if document_id is not None:
        document = docs.get(document_id, user.id)
    else:
        document = next(
            (
                row
                for row in docs.list_for_bike(bike_id, user.id)
                if row.document_type == "manufacturer_manual"
                and row.status == "active"
                and row.confirmed_at is not None
                and row.is_primary
            ),
            None,
        )
        if document is None:
            document = next(
                (
                    row
                    for row in docs.list_for_bike(bike_id, user.id)
                    if row.document_type == "manufacturer_manual"
                    and row.status == "active"
                    and row.confirmed_at is not None
                ),
                None,
            )
    if document is None or document.bike_id != bike_id:
        raise MaintenanceNotFound(
            "Confirm a manufacturer manual for this bike to build the maintenance plan."
        )
    pages = DocumentIngestionRepository(session).pages(document.id)
    return document.id, pages


@router.get("")
def list_maintenance(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
    bike_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        rows = service.list_for_bike(user, bike_id, limit=limit)
    except MaintenanceNotFound as exc:
        _raise(exc)
    return [MaintenanceResponse.model_validate(row) for row in rows]


@router.post("", status_code=201)
def create_maintenance(
    body: CreateMaintenanceBody,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        row = service.create(user, **body.model_dump())
    except (MaintenanceNotFound, InvalidMaintenance) as exc:
        _raise(exc)
    return MaintenanceResponse.model_validate(row)


@router.get("/{record_id}")
def get_maintenance(
    record_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        row = service.get(user, record_id)
    except MaintenanceNotFound as exc:
        _raise(exc)
    return MaintenanceResponse.model_validate(row)


@router.patch("/{record_id}")
def update_maintenance(
    record_id: UUID,
    body: UpdateMaintenanceBody,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        row = service.update(user, record_id, **body.model_dump(exclude_unset=True))
    except (MaintenanceNotFound, InvalidMaintenance) as exc:
        _raise(exc)
    return MaintenanceResponse.model_validate(row)


@router.delete("/{record_id}", status_code=204)
def delete_maintenance(
    record_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
):
    try:
        service.delete(user, record_id)
    except MaintenanceNotFound as exc:
        _raise(exc)
