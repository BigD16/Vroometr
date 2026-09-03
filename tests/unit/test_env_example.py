from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_has_no_values() -> None:
    for line_number, line in enumerate(
        (_REPO_ROOT / ".env.example").read_text().splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert "=" in stripped, f".env.example:{line_number} is not KEY="
        _key, _sep, value = stripped.partition("=")
        assert value == "", f".env.example:{line_number} must not set a value"


def test_env_example_lists_clerk_keys() -> None:
    text = (_REPO_ROOT / ".env.example").read_text()
    for key in (
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        "CLERK_SECRET_KEY",
        "CLERK_WEBHOOK_SECRET",
        "CLERK_JWKS_URL",
        "CLERK_AUTHORIZED_PARTY",
        "API_URL",
    ):
        assert f"{key}=" in text
