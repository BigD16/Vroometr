import os
import subprocess
import sys
from pathlib import Path


def test_api_launcher_can_publish_from_its_runtime_directory(tmp_path):
    root = Path(__file__).resolve().parents[2]
    launcher_root = tmp_path / "repo"
    (launcher_root / "scripts").mkdir(parents=True)
    for name in ("api-dev.sh", "load-env.sh"):
        (launcher_root / "scripts" / name).write_text((root / "scripts" / name).read_text())
    for name in ("libs", "services", "workers"):
        (launcher_root / name).symlink_to(root / name, target_is_directory=True)
    # CI supplies settings through the environment and has no root .env file.
    (launcher_root / ".env").write_text("# Settings are inherited by this test launcher.\n")
    # Exercise the real launcher with a stand-in uvicorn. No server or broker is needed.
    uvicorn = tmp_path / "uvicorn"
    uvicorn.write_text(
        f"#!{sys.executable}\n"
        "from uuid import uuid4\n"
        "from pathlib import Path\n"
        "from app.processing.dispatch import CeleryProcessingPublisher\n"
        "from app.repositories.attachment_processing import ProcessingMessage\n"
        "from workers.celery_app import celery_app\n"
        "assert Path.cwd().parts[-2:] == ('services', 'api')\n"
        "calls = []\n"
        "celery_app.send_task = lambda *a, **kw: calls.append((a, kw))\n"
        "message = ProcessingMessage(uuid4(), uuid4(), uuid4())\n"
        "CeleryProcessingPublisher().publish(message)\n"
        "assert calls == [(('vroometr.process_attachment',), {\n"
        "    'args': [str(message.user_id), str(message.attachment_id), str(message.attempt_id)],\n"
        "    'retry': False,\n"
        "})]\n"
        "print('publisher reachable from API launcher')\n"
    )
    uvicorn.chmod(0o755)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["API_HOST"] = "127.0.0.1"
    env["API_PORT"] = "0"
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    result = subprocess.run(
        ["bash", str(launcher_root / "scripts/api-dev.sh")], cwd=tmp_path, env=env,
        text=True, capture_output=True, timeout=20,
    )
    # Avoid including environment-derived output if the launcher fails.
    assert result.returncode == 0, "API launcher could not import and invoke its publisher"
    assert result.stdout.strip() == "publisher reachable from API launcher"
