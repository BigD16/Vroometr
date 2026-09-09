import { proxyFastApi } from "@/lib/fastapi";

export async function GET() {
  return proxyFastApi("/v1/bikes");
}
