import { proxyFastApi } from "@/lib/fastapi";

export async function POST(request: Request, { params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return proxyFastApi(`/v1/documents/${encodeURIComponent(documentId)}/confirm`, { method: "POST",
    headers: { "content-type": "application/json" }, body: await request.text() });
}
