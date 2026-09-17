from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from app.deps import get_attachment_link_service, get_current_user
from app.errors import AppError
from app.models.user import User
from app.services.attachment_links import (
    AttachmentLinkNotFound,
    AttachmentLinkService,
    AttachmentTargetNotFound,
    InvalidAttachmentLink,
)
from app.services.uploads import AttachmentNotFound, UploadNotComplete

router = APIRouter(prefix="/v1/attachment-links", tags=["attachments"])


class CreateAttachmentLinkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attachment_id: UUID
    entity_type: str
    entity_id: UUID
    relationship_type: str = "reference"


class AttachmentLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attachment_id: UUID
    entity_type: str
    entity_id: UUID
    relationship_type: str
    created_at: datetime


def _raise_link_error(exc: Exception) -> NoReturn:
    if isinstance(exc, InvalidAttachmentLink):
        raise AppError("invalid_attachment_link", str(exc), status_code=400) from exc
    if isinstance(exc, UploadNotComplete):
        raise AppError("upload_incomplete", str(exc), status_code=409) from exc
    if isinstance(exc, (AttachmentNotFound, AttachmentTargetNotFound, AttachmentLinkNotFound)):
        raise AppError("not_found", "Attachment or target not found", status_code=404) from exc
    raise exc


@router.post("")
def create_attachment_link(
    body: CreateAttachmentLinkBody,
    user: Annotated[User, Depends(get_current_user)],
    links: Annotated[AttachmentLinkService, Depends(get_attachment_link_service)],
) -> AttachmentLinkResponse:
    try:
        link = links.create(user, **body.model_dump())
    except (
        InvalidAttachmentLink,
        AttachmentNotFound,
        AttachmentTargetNotFound,
        UploadNotComplete,
    ) as exc:
        _raise_link_error(exc)
    return AttachmentLinkResponse.model_validate(link)


@router.get("")
def list_attachment_links(
    entity_type: str,
    entity_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    links: Annotated[AttachmentLinkService, Depends(get_attachment_link_service)],
) -> list[AttachmentLinkResponse]:
    try:
        records = links.list_for_entity(user, entity_type=entity_type, entity_id=entity_id)
    except (InvalidAttachmentLink, AttachmentTargetNotFound) as exc:
        _raise_link_error(exc)
    return [AttachmentLinkResponse.model_validate(link) for link in records]


@router.delete("/{link_id}", status_code=204)
def delete_attachment_link(
    link_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    links: Annotated[AttachmentLinkService, Depends(get_attachment_link_service)],
) -> Response:
    try:
        links.delete(user, link_id)
    except (AttachmentLinkNotFound, AttachmentTargetNotFound, InvalidAttachmentLink) as exc:
        _raise_link_error(exc)
    return Response(status_code=204)
