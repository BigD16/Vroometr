import "server-only";

import { notFound } from "next/navigation";

import { readApiError } from "@/lib/api-errors";
import type { Bike } from "@/lib/bikes";
import { proxyFastApi } from "@/lib/fastapi";

export async function loadBike(bikeId: string): Promise<Bike> {
  const response = await proxyFastApi(`/v1/bikes/${encodeURIComponent(bikeId)}`);
  if (response.status === 404 || response.status === 422) {
    notFound();
  }
  if (!response.ok) {
    const message = await readApiError(response, "Bike details are unavailable");
    throw new Error(`Bike details are unavailable (${response.status}): ${message}`);
  }
  return (await response.json()) as Bike;
}
