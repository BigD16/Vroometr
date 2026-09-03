# Repositories — SQLAlchemy queries live here, not in routes or Celery tasks.

`users.py` loads and saves the `users` row. Role and entitlement stay in this database; Clerk is only an identity proof.
