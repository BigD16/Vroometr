from datetime import date
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.deps import get_age_gate_service, get_current_user
from app.errors import AppError
from app.models.user import User
from app.services.age_gate import AgeGateService, InvalidAgeGate, UnderageBlocked

router = APIRouter(tags=["age-gate"])


class DateOfBirthBody(BaseModel):
    date_of_birth: date


class ConsentBody(BaseModel):
    """Signed-in user only. Extra fields such as minor_user_id are ignored."""

    model_config = ConfigDict(extra="ignore")

    guardian_contact: str
    consent_version: str


class EligibilityResponse(BaseModel):
    status: str
    date_of_birth: date | None


class ConsentResponse(BaseModel):
    id: UUID
    minor_user_id: UUID
    guardian_contact: str
    consent_version: str
    status: str


def _raise_age_gate(exc: InvalidAgeGate | UnderageBlocked) -> NoReturn:
    if isinstance(exc, UnderageBlocked):
        raise AppError("underage_blocked", str(exc), status_code=403) from exc
    raise AppError("invalid_age_gate", str(exc), status_code=400) from exc


@router.get("/v1/me/eligibility")
def eligibility(
    user: Annotated[User, Depends(get_current_user)],
    age_gate: Annotated[AgeGateService, Depends(get_age_gate_service)],
) -> EligibilityResponse:
    return EligibilityResponse(
        status=age_gate.eligibility(user).value,
        date_of_birth=user.date_of_birth,
    )


@router.post("/v1/me/date-of-birth")
def set_date_of_birth(
    body: DateOfBirthBody,
    user: Annotated[User, Depends(get_current_user)],
    age_gate: Annotated[AgeGateService, Depends(get_age_gate_service)],
) -> EligibilityResponse:
    try:
        updated = age_gate.set_date_of_birth(user, body.date_of_birth)
    except (InvalidAgeGate, UnderageBlocked) as exc:
        _raise_age_gate(exc)
    return EligibilityResponse(
        status=age_gate.eligibility(updated).value,
        date_of_birth=updated.date_of_birth,
    )


@router.post("/v1/parental-consents")
def record_parental_consent(
    body: ConsentBody,
    user: Annotated[User, Depends(get_current_user)],
    age_gate: Annotated[AgeGateService, Depends(get_age_gate_service)],
) -> ConsentResponse:
    """Records granted consent for the signed-in user. Client cannot pick another minor id."""
    try:
        consent = age_gate.record_granted(
            user,
            guardian_contact=body.guardian_contact,
            consent_version=body.consent_version,
        )
    except (InvalidAgeGate, UnderageBlocked) as exc:
        _raise_age_gate(exc)
    return ConsentResponse(
        id=consent.id,
        minor_user_id=consent.minor_user_id,
        guardian_contact=consent.guardian_contact,
        consent_version=consent.consent_version,
        status=consent.status,
    )
