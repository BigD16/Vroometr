import { proxyFastApi } from "@/lib/fastapi";

type BikeRouteContext = {
  params: Promise<{ bikeId: string }>;
};

function bikePath(bikeId: string): string {
  return `/v1/bikes/${encodeURIComponent(bikeId)}`;
}

export async function GET(_request: Request, { params }: BikeRouteContext) {
  const { bikeId } = await params;
  return proxyFastApi(bikePath(bikeId));
}

export async function PATCH(request: Request, { params }: BikeRouteContext) {
  const { bikeId } = await params;
  return proxyFastApi(bikePath(bikeId), {
    method: "PATCH",
    headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
    body: await request.text(),
  });
}
