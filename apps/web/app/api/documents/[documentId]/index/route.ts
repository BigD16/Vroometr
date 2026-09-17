import { proxyFastApi } from "@/lib/fastapi";

type Context = { params: Promise<{ documentId: string }> };
export async function GET(request: Request, { params }: Context) {
  const { documentId } = await params;
  const query = new URL(request.url).search;
  return proxyFastApi(`/v1/documents/${encodeURIComponent(documentId)}/index${query}`);
}
export async function POST(_request: Request, { params }: Context) {
  const { documentId } = await params;
  return proxyFastApi(`/v1/documents/${encodeURIComponent(documentId)}/index`, { method: "POST" });
}
