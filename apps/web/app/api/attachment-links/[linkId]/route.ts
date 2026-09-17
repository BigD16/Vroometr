import { proxyFastApi } from "@/lib/fastapi";

export async function DELETE(_request: Request, { params }: { params: Promise<{ linkId: string }> }) {
  const { linkId } = await params;
  return proxyFastApi(`/v1/attachment-links/${encodeURIComponent(linkId)}`, { method: "DELETE" });
}
