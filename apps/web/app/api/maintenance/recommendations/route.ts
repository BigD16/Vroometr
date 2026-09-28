import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const bikeId = url.searchParams.get("bike_id");
  const contextTags = url.searchParams.get("context_tags");
  const includeAi = url.searchParams.get("include_ai");
  const query = new URLSearchParams();
  if (bikeId) query.set("bike_id", bikeId);
  if (contextTags) query.set("context_tags", contextTags);
  if (includeAi) query.set("include_ai", includeAi);
  const suffix = query.toString() ? `?${query}` : "";
  return proxyFastApi(`/v1/maintenance/recommendations${suffix}`);
}
