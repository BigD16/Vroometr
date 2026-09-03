# Domain services — business rules live here, not in routes.

`users.py` creates and looks up Vroometr users. `clerk_sync.py` applies Clerk `user.created` / `user.updated` by calling `ensure`. Role and entitlement never come from Clerk metadata.
