import pytest

from vroometr.flags import use_in_memory_flags


@pytest.fixture(autouse=True)
def _in_memory_flags() -> None:
    """Tests never talk to Unleash."""
    use_in_memory_flags()
