from pipelines.health import process
from workers.tasks import health


def test_health_pipeline() -> None:
    assert process() == {"status": "ok"}


def test_health_task_delegates_to_pipeline() -> None:
    assert health.run() == {"status": "ok"}


def test_attachment_task_delegates_to_pipeline(monkeypatch):
    from workers import tasks

    calls = []

    def process(*args):
        calls.append(args)
        return {"status": "completed"}

    monkeypatch.setattr(tasks.attachment_pipeline, "process", process)
    assert tasks.process_attachment.run("owner", "file", "attempt") == {"status": "completed"}
    assert calls == [("owner", "file", "attempt")]
