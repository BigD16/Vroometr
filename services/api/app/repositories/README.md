# Repositories — SQLAlchemy queries live here, not in routes or Celery tasks.

`users.py` loads and saves the `users` row, including its persistent active-bike reference. Role and entitlement stay in this database; Clerk is only an identity proof.

`parental_consents.py` stores versioned guardian approvals for 13–17 users.

`bikes.py` loads and saves owner-scoped machines. `get` and `list_for_user` always filter by `user_id` so another rider's bike is never returned.

`attachments.py` loads and saves upload metadata. Every lookup includes both attachment id and
owner id so unknown and foreign attachments have the same not-found behavior.
