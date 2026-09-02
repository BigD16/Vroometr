from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_NAV = (_WEB / "lib" / "nav.ts").read_text()
_DASHBOARD = "\n".join(
    path.read_text()
    for path in (_WEB / "components" / "dashboard").glob("*.tsx")
)


def test_locked_nav_routes_are_listed() -> None:
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


def test_dashboard_cards_do_not_surface_issues() -> None:
    assert "issue" not in _DASHBOARD.lower()
