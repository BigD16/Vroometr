from uuid import UUID, uuid4

import pytest
from app.models.attachment import Attachment
from app.models.attachment_link import AttachmentLink
from app.models.bike import Bike
from app.models.user import User
from app.services.attachment_links import (
    AttachmentLinkNotFound,
    AttachmentLinkService,
    AttachmentTargetNotFound,
    InvalidAttachmentLink,
)
from app.services.uploads import AttachmentNotFound, UploadNotComplete
from tests.unit.fakes import InMemoryBikeRepository


class Attachments:
    def lock_owner(self, user_id: UUID) -> None:
        pass

    def __init__(self, attachment: Attachment) -> None:
        self.attachment = attachment

    def get(self, attachment_id: UUID, user_id: UUID) -> Attachment | None:
        if self.attachment.id == attachment_id and self.attachment.user_id == user_id:
            return self.attachment
        return None


class Links:
    def __init__(self, attachments: Attachments) -> None:
        self.items: dict[UUID, AttachmentLink] = {}
        self.attachments = attachments

    def get(self, link_id: UUID, user_id: UUID) -> AttachmentLink | None:
        link = self.items.get(link_id)
        if link and self.attachments.get(link.attachment_id, user_id):
            return link
        return None

    def list_for_user(self, user_id):
        return [link for link in self.items.values() if self.get(link.id, user_id)]

    def list_for_entity(self, entity_type, entity_id, user_id):
        return [
            link
            for link in self.items.values()
            if link.entity_type == entity_type
            and link.entity_id == entity_id
            and self.get(link.id, user_id)
        ]

    def add(self, link: AttachmentLink) -> AttachmentLink:
        for existing in self.items.values():
            if all(
                getattr(existing, key) == getattr(link, key)
                for key in (
                    "attachment_id",
                    "entity_type",
                    "entity_id",
                    "relationship_type",
                )
            ):
                return existing
        self.items[link.id] = link
        return link

    def delete(self, link: AttachmentLink) -> None:
        del self.items[link.id]


def make_link_setup():
    owner = User(id=uuid4())
    other = User(id=uuid4())
    bikes = InMemoryBikeRepository()
    bike = bikes.add(Bike(id=uuid4(), user_id=owner.id))
    second = bikes.add(Bike(id=uuid4(), user_id=owner.id))
    foreign = bikes.add(Bike(id=uuid4(), user_id=other.id))
    attachment = Attachment(id=uuid4(), user_id=owner.id, status="uploaded")
    attachments = Attachments(attachment)
    links = Links(attachments)
    service = AttachmentLinkService(links, attachments, bikes)
    return service, owner, other, bike, second, foreign, attachment, links


def create(service, owner, bike, attachment, **overrides):
    values = dict(
        attachment_id=attachment.id,
        entity_type="bike",
        entity_id=bike.id,
        relationship_type="reference",
    )
    values.update(overrides)
    return service.create(owner, **values)


def test_file_reuse_retry_and_unlink_preserve_other_relationships(link_setup):
    service, owner, _, bike, second, _, attachment, _ = link_setup
    first = create(service, owner, bike, attachment)
    assert create(service, owner, bike, attachment).id == first.id
    retained = create(service, owner, second, attachment)
    service.delete(owner, first.id)
    assert service.list_for_entity(owner, entity_type="bike", entity_id=bike.id) == []
    assert service.list_for_entity(owner, entity_type="bike", entity_id=second.id) == [retained]
    assert attachment.status == "uploaded"


def test_both_sides_require_ownership(link_setup):
    service, owner, other, bike, _, foreign, attachment, links = link_setup
    with pytest.raises(AttachmentTargetNotFound):
        create(service, owner, foreign, attachment)
    with pytest.raises(AttachmentTargetNotFound):
        create(service, owner, bike, attachment, entity_id=uuid4())
    with pytest.raises(AttachmentNotFound):
        create(service, other, foreign, attachment)
    with pytest.raises(AttachmentNotFound):
        create(service, owner, bike, attachment, attachment_id=uuid4())
    assert not links.items
    link = create(service, owner, bike, attachment)
    with pytest.raises(AttachmentLinkNotFound):
        service.delete(other, link.id)
    with pytest.raises(AttachmentTargetNotFound):
        service.list_for_entity(other, entity_type="bike", entity_id=bike.id)
    assert link.id in links.items


def test_pending_upload_cannot_be_linked(link_setup):
    service, owner, _, bike, _, _, attachment, links = link_setup
    attachment.status = "pending"
    with pytest.raises(UploadNotComplete):
        create(service, owner, bike, attachment)
    assert not links.items


@pytest.mark.parametrize(
    "overrides",
    [
        {"entity_type": "maintenance_record"},
        {"entity_type": "unknown"},
        {"relationship_type": "  "},
        {"relationship_type": "x" * 33},
    ],
)
def test_unsupported_targets_and_invalid_relationships_fail_closed(link_setup, overrides):
    service, owner, _, bike, _, _, attachment, links = link_setup
    with pytest.raises(InvalidAttachmentLink):
        create(service, owner, bike, attachment, **overrides)
    assert not links.items


@pytest.fixture
def link_setup():
    return make_link_setup()
