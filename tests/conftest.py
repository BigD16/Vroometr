import os
from pathlib import Path

import pytest

from vroometr.flags import use_in_memory_flags

_REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_configure() -> None:
    if (_REPO_ROOT / ".env").exists():
        return
    # GitHub Actions sets CI=true and passes values as job env vars instead of a file.
    if os.environ.get("CI"):
        return
    pytest.exit("Missing .env. Copy .env.example to .env and fill in every value.")


@pytest.fixture(autouse=True)
def _in_memory_flags() -> None:
    """Tests never talk to Unleash."""
    use_in_memory_flags()
