import { proxyFastApi } from "@/lib/fastapi";

type BikeRouteContext = {
  params: Promise<{ bikeId: string }>;
};

export async function POST(request: Request, { params }: BikeRouteContext) {
  const { bikeId } = await params;
  return proxyFastApi(`/v1/bikes/${encodeURIComponent(bikeId)}/engine-hours`, {
    method: "POST",
    headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
    body: await request.text(),
  });
}
