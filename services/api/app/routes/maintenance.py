from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.deps import get_current_user, get_maintenance_service
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
    active: bool
    created_at: datetime
    updated_at: datetime


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


@router.get("/rules")
def list_rules(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MaintenanceService, Depends(get_maintenance_service)],
    bike_id: UUID = Query(...),
):
    try:
        rows = service.list_rules(user, bike_id)
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
