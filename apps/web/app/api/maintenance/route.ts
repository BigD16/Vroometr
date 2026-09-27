import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const bikeId = url.searchParams.get("bike_id");
  const limit = url.searchParams.get("limit");
  const params = new URLSearchParams();
  if (bikeId) params.set("bike_id", bikeId);
  if (limit) params.set("limit", limit);
  const query = params.toString() ? `?${params}` : "";
  return proxyFastApi(`/v1/maintenance${query}`);
}

export async function POST(request: Request) {
  return proxyFastApi("/v1/maintenance", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
