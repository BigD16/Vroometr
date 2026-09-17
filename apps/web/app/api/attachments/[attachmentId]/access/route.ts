import { proxyFastApi } from "@/lib/fastapi";

export async function GET(request: Request, { params }: { params: Promise<{ attachmentId: string }> }) {
  const { attachmentId } = await params;
  const query = new URLSearchParams({ download: new URL(request.url).searchParams.get("download") ?? "true" });
  return proxyFastApi(`/v1/attachments/${encodeURIComponent(attachmentId)}/access?${query}`);
}
