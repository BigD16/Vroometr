import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request) {
  const source = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  for (const key of ["bike_id", "include_all"]) {
    const value = source.get(key);
    if (value !== null) query.set(key, value);
  }
  return proxyFastApi(`/v1/attachments?${query}`);
}
