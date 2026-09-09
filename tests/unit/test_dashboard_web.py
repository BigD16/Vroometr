from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_DASHBOARD = _WEB / "components" / "dashboard"
_PAGE = (_WEB / "app" / "(shell)" / "page.tsx").read_text()
_OVERVIEW = (_DASHBOARD / "DashboardOverview.tsx").read_text()
_MACHINE_STATUS = (_DASHBOARD / "MachineStatus.tsx").read_text()
_HEALTH = (_DASHBOARD / "MachineHealthCard.tsx").read_text()
_UP_NEXT = (_DASHBOARD / "UpNextCard.tsx").read_text()
_RIDE = (_DASHBOARD / "PlannedRideCard.tsx").read_text()
_METRICS = (_DASHBOARD / "MetricsStrip.tsx").read_text()
_ASSISTANT_FAB = (_WEB / "components" / "AssistantFab.tsx").read_text()


def test_dashboard_uses_server_hydrated_active_bike_context() -> None:
    assert "<DashboardOverview />" in _PAGE
    assert "useActiveBike()" in _OVERVIEW
    assert "<MachineStatus bike={activeBike} />" in _OVERVIEW
    assert "<MetricsStrip bike={activeBike} />" in _OVERVIEW
    assert "useActiveBike()" in _ASSISTANT_FAB


def test_dashboard_renders_live_bike_facts() -> None:
    assert "bike.nickname" in _MACHINE_STATUS
    assert "bike.powertrain_type" in _MACHINE_STATUS
    assert "current_engine_hours" in _METRICS
    assert "current_engine_hours_is_estimated" in _METRICS
    assert "bike.powertrain_type" in _METRICS


def test_unbuilt_domains_are_honest_empty_states() -> None:
    assert "NOT CALCULATED" in _HEALTH
    assert "verified maintenance data" in _HEALTH
    assert "No verified tasks yet" in _UP_NEXT
    assert "Nothing scheduled" in _RIDE
    assert "NO HISTORY" in _METRICS


def test_dashboard_contains_no_legacy_mock_machine_data() -> None:
    dashboard_source = "\n".join(
        path.read_text() for path in sorted(_DASHBOARD.glob("*.tsx"))
    )
    assert "mock-machine" not in dashboard_source
    assert "Glen Helen" not in dashboard_source
    assert "READY TO RIDE" not in dashboard_source
    assert "healthPercent" not in dashboard_source
    assert not (_WEB / "lib" / "mock-machine.ts").exists()
