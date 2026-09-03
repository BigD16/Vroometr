from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_PUBLIC_ROUTES = (_WEB / "lib" / "public-routes.ts").read_text()
_PROXY = (_WEB / "proxy.ts").read_text()
_NAV = (_WEB / "lib" / "nav.ts").read_text()


def is_public_path(pathname: str) -> bool:
    path = pathname.split("?", 1)[0]
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in ("/sign-in", "/sign-up", "/api")
    )


def test_proxy_protects_non_public_routes() -> None:
    assert "createRouteMatcher" in _PROXY
    assert "auth.protect" in _PROXY
    assert "PUBLIC_ROUTE_PATTERNS" in _PROXY


def test_sign_in_and_sign_up_are_public_patterns() -> None:
    assert '"/sign-in(.*)"' in _PUBLIC_ROUTES
    assert '"/sign-up(.*)"' in _PUBLIC_ROUTES


def test_next_api_bff_is_not_turned_into_a_clerk_404() -> None:
    assert '"/api(.*)"' in _PUBLIC_ROUTES


def test_shell_paths_are_not_public() -> None:
    for href in (
        "/",
        "/garage",
        "/assistant",
        "/maintenance",
        "/rides",
        "/documents",
        "/modifications",
        "/issues",
        "/settings",
        "/suspension",
    ):
        assert href in _NAV
        assert not is_public_path(href)
        assert not is_public_path(href + "/nested")


def test_clerk_and_bff_paths_are_public() -> None:
    for pathname in (
        "/sign-in",
        "/sign-in/sso-callback",
        "/sign-up",
        "/sign-up/verify",
        "/api/me",
    ):
        assert is_public_path(pathname)
