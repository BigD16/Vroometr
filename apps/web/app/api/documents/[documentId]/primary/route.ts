import { proxyFastApi } from "@/lib/fastapi";

export async function PUT(_request: Request, { params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return proxyFastApi(`/v1/documents/${encodeURIComponent(documentId)}/primary`, { method: "PUT" });
}
