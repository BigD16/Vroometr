import "server-only";

import type { ActiveBikeSnapshot, BikeSummary } from "@/lib/bikes";
import { proxyFastApi } from "@/lib/fastapi";

async function responseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return body.error?.message ?? "Bike context is unavailable";
  } catch {
    return "Bike context is unavailable";
  }
}

export async function loadActiveBikeSnapshot(): Promise<ActiveBikeSnapshot> {
  const [bikesResponse, activeResponse] = await Promise.all([
    proxyFastApi("/v1/bikes"),
    proxyFastApi("/v1/me/active-bike"),
  ]);
  if (!bikesResponse.ok) {
    return { bikes: [], activeBikeId: null, error: await responseError(bikesResponse) };
  }
  if (!activeResponse.ok) {
    return { bikes: [], activeBikeId: null, error: await responseError(activeResponse) };
  }

  const bikes = (await bikesResponse.json()) as BikeSummary[];
  const active = (await activeResponse.json()) as { active_bike_id: string | null };
  return { bikes, activeBikeId: active.active_bike_id, error: null };
}
