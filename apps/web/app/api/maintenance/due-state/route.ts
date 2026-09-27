import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const bikeId = new URL(request.url).searchParams.get("bike_id");
  const query = bikeId ? `?bike_id=${encodeURIComponent(bikeId)}` : "";
  return proxyFastApi(`/v1/maintenance/due-state${query}`);
}
