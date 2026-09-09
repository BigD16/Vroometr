import { proxyFastApi } from "@/lib/fastapi";

export async function GET() {
  return proxyFastApi("/v1/bikes");
}

export async function POST(request: Request) {
  return proxyFastApi("/v1/bikes", {
    method: "POST",
    headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
    body: await request.text(),
  });
}
