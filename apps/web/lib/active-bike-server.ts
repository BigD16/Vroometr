import "server-only";

import { readApiError } from "@/lib/api-errors";
import type { ActiveBikeSnapshot, Bike } from "@/lib/bikes";
import { proxyFastApi } from "@/lib/fastapi";

export async function loadActiveBikeSnapshot(): Promise<ActiveBikeSnapshot> {
  const [bikesResponse, activeResponse] = await Promise.all([
    proxyFastApi("/v1/bikes"),
    proxyFastApi("/v1/me/active-bike"),
  ]);
  if (!bikesResponse.ok) {
    return {
      bikes: [],
      activeBikeId: null,
      error: await readApiError(bikesResponse, "Bike context is unavailable"),
    };
  }
  if (!activeResponse.ok) {
    return {
      bikes: [],
      activeBikeId: null,
      error: await readApiError(activeResponse, "Bike context is unavailable"),
    };
  }

  const bikes = (await bikesResponse.json()) as Bike[];
  const active = (await activeResponse.json()) as { active_bike_id: string | null };
  return { bikes, activeBikeId: active.active_bike_id, error: null };
}
