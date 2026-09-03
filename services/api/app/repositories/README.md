# Repositories — SQLAlchemy queries live here, not in routes or Celery tasks.

`users.py` loads and saves the `users` row. Role and entitlement stay in this database; Clerk is only an identity proof.

`parental_consents.py` stores versioned guardian approvals for 13–17 users.

`bikes.py` loads and saves owner-scoped machines. `get` and `list_for_user` always filter by `user_id` so another rider's bike is never returned.
