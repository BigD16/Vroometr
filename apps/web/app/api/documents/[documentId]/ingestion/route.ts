import { proxyFastApi } from "@/lib/fastapi";

type Context = { params: Promise<{ documentId: string }> };

export async function GET(_request: Request, { params }: Context) {
  const { documentId } = await params;
  return proxyFastApi(`/v1/documents/${encodeURIComponent(documentId)}/ingestion`);
}

export async function POST(_request: Request, { params }: Context) {
  const { documentId } = await params;
  return proxyFastApi(`/v1/documents/${encodeURIComponent(documentId)}/ingestion`, { method: "POST" });
}
