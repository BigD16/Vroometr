from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_PROVIDER = (_WEB / "components" / "ActiveBikeProvider.tsx").read_text()
_TOP_HUD = (_WEB / "components" / "TopHud.tsx").read_text()
_SHELL = (_WEB / "components" / "GarageShell.tsx").read_text()
_ASSISTANT_FAB = (_WEB / "components" / "AssistantFab.tsx").read_text()
_BIKES_ROUTE = (_WEB / "app" / "api" / "bikes" / "route.ts").read_text()
_ACTIVE_ROUTE = (_WEB / "app" / "api" / "me" / "active-bike" / "route.ts").read_text()


def test_shell_provides_persisted_active_bike_context() -> None:
    assert "<ActiveBikeProvider" in _SHELL
    assert 'fetch("/api/bikes"' in _PROVIDER
    assert 'fetch("/api/me/active-bike"' in _PROVIDER
    assert 'method: "PUT"' in _PROVIDER


def test_hud_uses_real_bike_selector_not_mock_machine() -> None:
    assert "<ActiveBikeSelector />" in _TOP_HUD
    assert "mockMachine" not in _TOP_HUD
    assert "useActiveBike()" in _ASSISTANT_FAB


def test_next_routes_proxy_bike_context_to_fastapi() -> None:
    assert 'proxyFastApi("/v1/bikes")' in _BIKES_ROUTE
    assert 'proxyFastApi("/v1/me/active-bike")' in _ACTIVE_ROUTE
    assert "export async function PUT" in _ACTIVE_ROUTE
