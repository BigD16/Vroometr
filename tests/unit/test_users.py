import pytest
from app.models.user import Entitlement, Role
from app.repositories.users import UserAlreadyExists
from app.services.users import InvalidUserAccess, UserService
from tests.unit.fakes import InMemoryUserRepository


def _service() -> UserService:
    return UserService(InMemoryUserRepository())


def test_create_defaults_to_user_and_none_entitlement() -> None:
    user = _service().create("user_clerk_abc")
    assert user.clerk_user_id == "user_clerk_abc"
    assert user.role == Role.USER.value
    assert user.entitlement == Entitlement.NONE.value


def test_create_can_set_admin_and_tester() -> None:
    user = _service().create(
        "user_clerk_admin",
        role=Role.ADMIN,
        entitlement=Entitlement.TESTER,
    )
    assert user.role == Role.ADMIN.value
    assert user.entitlement == Entitlement.TESTER.value


def test_get_by_clerk_user_id() -> None:
    service = _service()
    created = service.create("user_clerk_lookup")
    found = service.get_by_clerk_user_id("user_clerk_lookup")
    assert found is not None
    assert found.id == created.id
    assert service.get_by_id(created.id) is found


def test_duplicate_clerk_user_id_is_rejected() -> None:
    service = _service()
    service.create("user_clerk_dup")
    with pytest.raises(UserAlreadyExists):
        service.create("user_clerk_dup")


def test_blank_clerk_user_id_is_rejected() -> None:
    with pytest.raises(InvalidUserAccess):
        _service().create("   ")


def test_invalid_role_is_rejected() -> None:
    with pytest.raises(InvalidUserAccess):
        _service().create("user_clerk_bad", role="superadmin")  # type: ignore[arg-type]
