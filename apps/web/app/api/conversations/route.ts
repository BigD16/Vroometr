import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const bikeId = new URL(request.url).searchParams.get("bike_id");
  const query = bikeId ? `?bike_id=${encodeURIComponent(bikeId)}` : "";
  return proxyFastApi(`/v1/conversations${query}`);
}

export async function POST(request: Request) {
  return proxyFastApi("/v1/conversations", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
