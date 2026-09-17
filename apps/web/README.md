# Website (`apps/web`)

See the [implementation guide](../../docs/developer-guide.md) for the backend rules behind the
UI and the [runbook](../../docs/development-runbook.md) for setup and manual smoke review.

Next.js App Router UI. The garage HUD, Garage pages, and dashboard load owner-scoped bike rows through FastAPI. Garage supports combustion and electric bikes across list, create, dedicated detail, edit, archive, and restore flows. Dashboard identity, powertrain, engine hours, and Assistant context are live; maintenance and ride areas show empty states until those domains are implemented. Documents supports direct private uploads, active-bike and account file lists, sandboxed previews/downloads, unlink/relink, and confirmed file deletion. Account usage includes pending uploads. New uploads become deletable when their 15-minute upload grant expires.

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
| Document library / file actions | `components/DocumentLibrary.tsx`, `components/DocumentsWorkspace.tsx`, `app/api/attachments/` |
| Processing status / retry | `components/ProcessingStatus.tsx`, `app/api/attachments/[attachmentId]/processing/` |
| Direct document upload | `components/DocumentUpload.tsx`, `app/api/uploads/` |
| Top bar, left rail, scene, FAB | `components/` |
| Dashboard cards | `components/dashboard/` |
| Look (glass, type, spacing) | `app/globals.css` |
| Settings stubs | `app/(shell)/settings/` |
| A screen | `app/(shell)/…/page.tsx` |
| Data or permissions | `services/api`, not here |

Documents polls persisted processing status and supports retries. Checks finished with
Not scanned means the scanner is not configured; it is not a clean verdict. Infected files
have View/Download disabled and are also blocked by the backend.

`DocumentRecords.tsx` adds PDF registration, make/model/year confirmation, duplicate warnings,
edition history, primary manual selection, and private download to DocumentsWorkspace.
The initial metadata is copied from the bike profile, not inferred from the PDF. File changes
refresh the record section. Server rules live in `app/services/documents.py` under the API.

`DocumentIngestion.tsx` adds Extract pages, durable status polling, incomplete-page retries,
and escaped page-text excerpts to confirmed document records. OCR/vision routes are explicitly
provider-pending. API errors clear previously displayed text on refresh. See the
[4.2 handoff](../../docs/implementation-progress.md#page-ingestion-42--2026-09-11).

`DocumentIndex.tsx` adds Build sections & embeddings and paginated chunk review, including
section parents, physical pages, source offsets, and pending/configuration/stale labels.
The build action explains that embeddings send extracted text to the provider. See the
[indexing handoff](../../docs/document-indexing.md).

`DocumentSearch.tsx` adds Search bike documents above the library. `/api/retrieval` forwards
owner-authenticated searches to FastAPI. Results preserve source text, section/page citations,
primary/archive and partial labels, plus a View source PDF action using existing private access
grants. A checkbox explicitly includes reference editions. Search handles loading, missing
sources/evidence, provider errors, and late responses after bike switching. See the
[retrieval handoff](../../docs/document-retrieval.md) for setup and review steps.
