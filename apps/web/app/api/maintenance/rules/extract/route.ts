import { proxyFastApi } from "@/lib/fastapi";

export async function POST(request: Request) {
  return proxyFastApi("/v1/maintenance/rules/extract", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
