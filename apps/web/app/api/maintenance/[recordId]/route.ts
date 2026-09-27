import { proxyFastApi } from "@/lib/fastapi";

type Params = { params: Promise<{ recordId: string }> };

export async function GET(_request: Request, { params }: Params) {
  const { recordId } = await params;
  return proxyFastApi(`/v1/maintenance/${recordId}`);
}

export async function PATCH(request: Request, { params }: Params) {
  const { recordId } = await params;
  return proxyFastApi(`/v1/maintenance/${recordId}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}

export async function DELETE(_request: Request, { params }: Params) {
  const { recordId } = await params;
  return proxyFastApi(`/v1/maintenance/${recordId}`, { method: "DELETE" });
}
