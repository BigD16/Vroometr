import json

import pytest
from app.db import engine
from evals.manual_corpus import corpus
from evals.manuals import FIXTURES, Embeddings
from sqlalchemy import text


def test_eval_rows_rollback_on_failure():
    try:
        with engine.connect() as connection:
            before = connection.scalar(
                text("SELECT count(*) FROM users WHERE clerk_user_id LIKE 'eval-%'")
            )
    except Exception:
        pytest.skip("Postgres is not running")
    dataset = json.loads((FIXTURES / "manual_cases.json").read_text())
    tape = json.loads((FIXTURES / "manual_replay.json").read_text())
    with pytest.raises(RuntimeError, match="deliberate evaluation failure"):
        with corpus(dataset, Embeddings(tape["embeddings"]), "recorded", "eval-v1") as rows:
            assert (
                rows[0].scalar(text("SELECT count(*) FROM users WHERE clerk_user_id LIKE 'eval-%'"))
                == before + 1
            )
            raise RuntimeError("deliberate evaluation failure")
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT count(*) FROM users WHERE clerk_user_id LIKE 'eval-%'"))
            == before
        )
