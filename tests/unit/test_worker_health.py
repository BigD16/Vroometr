from pipelines.health import process
from workers.tasks import health


def test_health_pipeline() -> None:
    assert process() == {"status": "ok"}


def test_health_task_delegates_to_pipeline() -> None:
    assert health.run() == {"status": "ok"}
