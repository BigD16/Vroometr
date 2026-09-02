# Tests

- `tests/unit/` — domain and helper tests
- Integration tests (database, S3) land here later

```bash
source .venv/bin/activate
pytest
```

Pytest needs a filled-in `.env` at the repo root locally. GitHub Actions sets `CI=true` and supplies the same keys as job environment variables instead.
