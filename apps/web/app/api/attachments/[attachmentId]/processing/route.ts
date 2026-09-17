import { proxyFastApi } from "@/lib/fastapi";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ attachmentId: string }> },
) {
  const { attachmentId } = await params;
  return proxyFastApi(`/v1/attachments/${encodeURIComponent(attachmentId)}/processing`, {
    method: "POST",
  });
}
