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

| If you want to change… | Open |
| --- | --- |
| Nav items / scene per route | `lib/nav.ts` |
| Placeholder bike copy | `lib/mock-machine.ts` |
| Top bar, left rail, scene, FAB | `components/` |
| Dashboard cards | `components/dashboard/` |
| Look (glass, type, spacing) | `app/globals.css` |
| A screen | `app/(shell)/…/page.tsx` |
| Data or permissions | `services/api`, not here |
