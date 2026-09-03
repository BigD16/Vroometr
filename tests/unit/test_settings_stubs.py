from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_SETTINGS = _WEB / "app" / "(shell)" / "settings"


def test_settings_has_account_notifications_and_privacy_stubs() -> None:
    account = (_SETTINGS / "page.tsx").read_text()
    notifications = (_SETTINGS / "notifications" / "page.tsx").read_text()
    privacy = (_SETTINGS / "privacy" / "page.tsx").read_text()
    subnav = (_WEB / "components" / "SettingsSubnav.tsx").read_text()

    assert "Clerk" in account
    assert "Vroometr" in account
    assert "/v1/bikes" in account
    assert "Payment failure" in notifications
    assert "cannot disable" in notifications
    assert "Delete account" in privacy
    assert "Allow my data to help improve Vroometr" in privacy
    assert "/settings/notifications" in subnav
    assert "/settings/privacy" in subnav
    assert "Data & Privacy" in subnav
