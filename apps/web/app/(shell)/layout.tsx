import type { ReactNode } from "react";

import { GarageShell } from "@/components/GarageShell";
import { loadActiveBikeSnapshot } from "@/lib/active-bike-server";

export const dynamic = "force-dynamic";

export default async function ShellLayout({ children }: { children: ReactNode }) {
  const initialBikeContext = await loadActiveBikeSnapshot();
  return <GarageShell initialBikeContext={initialBikeContext}>{children}</GarageShell>;
}
