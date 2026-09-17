import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const query = new URLSearchParams({ bike_id: new URL(request.url).searchParams.get("bike_id") ?? "" });
  return proxyFastApi(`/v1/documents?${query}`);
}
export async function POST(request: Request) {
  return proxyFastApi("/v1/documents", { method: "POST",
    headers: { "content-type": "application/json" }, body: await request.text() });
}
