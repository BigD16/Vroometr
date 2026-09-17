import { proxyFastApi } from "@/lib/fastapi";

export async function DELETE(request: Request, { params }: { params: Promise<{ attachmentId: string }> }) {
  const { attachmentId } = await params;
  return proxyFastApi(`/v1/attachments/${encodeURIComponent(attachmentId)}`, {
    method: "DELETE", headers: { "content-type": "application/json" }, body: await request.text(),
  });
}
