import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const bikeId = url.searchParams.get("bike_id");
  const includeInactive = url.searchParams.get("include_inactive");
  const query = new URLSearchParams();
  if (bikeId) query.set("bike_id", bikeId);
  if (includeInactive) query.set("include_inactive", includeInactive);
  const suffix = query.toString() ? `?${query}` : "";
  return proxyFastApi(`/v1/maintenance/rules${suffix}`);
}

export async function POST(request: Request) {
  return proxyFastApi("/v1/maintenance/rules", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
