# Website (`apps/web`)

Next.js App Router UI. The garage HUD, Garage pages, and dashboard load owner-scoped bike rows through FastAPI. Garage supports combustion and electric bikes across list, create, dedicated detail, edit, archive, and restore flows. Dashboard identity, powertrain, engine hours, and Assistant context are live; maintenance and ride areas show empty states until those domains are implemented. Documents can send validated files directly from the browser to private S3 storage.

Scene stills live in `public/`:

- `default-garage.jpg` — garage / dashboard backdrop
- `rides-track.jpg` — rides backdrop

```bash
cd apps/web && npm install && cd ../..
./scripts/web-dev.sh
```

Run those commands from the repo root, then open http://localhost:3000. The wrapper loads server-side settings such as `API_URL` from the repo-root `.env`; Next.js still loads Clerk's browser keys from `apps/web/.env.local` when present.

Sign-in is `/sign-in` (needs Clerk keys in the repo-root `.env` or `apps/web/.env.local`). The garage HUD and other `(shell)` routes require a Clerk session; signed-out visits redirect to sign-in. After sign-in, http://localhost:3000/api/me proxies the FastAPI `/v1/me` row (role/entitlement from Postgres). Middleware is a UX gate only — FastAPI still authorizes `/v1/*`.

| If you want to change… | Open |
| --- | --- |
| Nav items / scene per route | `lib/nav.ts` |
| Dashboard active-bike composition | `components/dashboard/DashboardOverview.tsx` |
| Sign-in / profile | `app/sign-in/`, `components/ProfileControl.tsx` |
| Clerk wiring | `proxy.ts`, `components/ClerkProviders.tsx` |
| Public vs protected paths | `lib/public-routes.ts`, `proxy.ts` |
| Active-bike state / selector | `components/ActiveBikeProvider.tsx`, `components/ActiveBikeSelector.tsx` |
| Garage list / machine forms | `components/GarageList.tsx`, `components/BikeForm.tsx` |
| Per-bike detail UI | `components/BikeDetails.tsx`, `app/(shell)/garage/[bikeId]/` |
| Direct document upload | `components/DocumentUpload.tsx`, `app/api/uploads/` |
| Top bar, left rail, scene, FAB | `components/` |
| Dashboard cards | `components/dashboard/` |
| Look (glass, type, spacing) | `app/globals.css` |
| Settings stubs | `app/(shell)/settings/` |
| A screen | `app/(shell)/…/page.tsx` |
| Data or permissions | `services/api`, not here |
