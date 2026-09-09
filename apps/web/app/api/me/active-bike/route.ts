import { proxyFastApi } from "@/lib/fastapi";

export async function GET() {
  return proxyFastApi("/v1/me/active-bike");
}

export async function PUT(request: Request) {
  return proxyFastApi("/v1/me/active-bike", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
