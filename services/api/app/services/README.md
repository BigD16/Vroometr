# Domain services — business rules live here, not in routes.

`users.py` creates and looks up Vroometr users. `clerk_sync.py` applies Clerk `user.created` / `user.updated` by calling `ensure`. Role and entitlement never come from Clerk metadata.

`age_gate.py` decides eligibility from date of birth and versioned guardian consent. 18+ may use Vroometr directly; 13–17 need a granted consent; under-13 dates of birth are rejected and not stored.

`bikes.py` creates, lists, reads, and updates bikes for the signed-in user. Owner id always comes from the session user, never from a client-supplied `user_id`.
