import { proxyFastApi } from "@/lib/fastapi";

type Params = { params: Promise<{ conversationId: string }> };

export async function GET(_request: Request, { params }: Params) {
  const { conversationId } = await params;
  return proxyFastApi(`/v1/conversations/${encodeURIComponent(conversationId)}`);
}

export async function DELETE(_request: Request, { params }: Params) {
  const { conversationId } = await params;
  return proxyFastApi(`/v1/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
}
