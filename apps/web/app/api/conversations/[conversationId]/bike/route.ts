import { proxyFastApi } from "@/lib/fastapi";

type Params = { params: Promise<{ conversationId: string }> };

export async function POST(request: Request, { params }: Params) {
  const { conversationId } = await params;
  return proxyFastApi(`/v1/conversations/${encodeURIComponent(conversationId)}/bike`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
