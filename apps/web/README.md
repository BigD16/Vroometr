# Website (`apps/web`)

Next.js App Router UI. The garage HUD is a static visual shell (placeholder bike copy).

Scene stills live in `public/`:

- `default-garage.jpg` — garage / dashboard backdrop
- `rides-track.jpg` — rides backdrop

```bash
npm install
npm run dev
```

Then open http://localhost:3000

Sign-in is `/sign-in` (needs Clerk keys in the repo-root `.env` or `apps/web/.env.local`). The garage HUD and other `(shell)` routes require a Clerk session; signed-out visits redirect to sign-in. After sign-in, http://localhost:3000/api/me proxies the FastAPI `/v1/me` row (role/entitlement from Postgres). Middleware is a UX gate only — FastAPI still authorizes `/v1/*`.

| If you want to change… | Open |
| --- | --- |
| Nav items / scene per route | `lib/nav.ts` |
| Placeholder bike copy | `lib/mock-machine.ts` |
| Sign-in / profile | `app/sign-in/`, `components/ProfileControl.tsx` |
| Clerk wiring | `proxy.ts`, `components/ClerkProviders.tsx` |
| Public vs protected paths | `lib/public-routes.ts`, `proxy.ts` |
| Top bar, left rail, scene, FAB | `components/` |
| Dashboard cards | `components/dashboard/` |
| Look (glass, type, spacing) | `app/globals.css` |
| Settings stubs | `app/(shell)/settings/` |
| A screen | `app/(shell)/…/page.tsx` |
| Data or permissions | `services/api`, not here |
