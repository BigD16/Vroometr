import { proxyFastApi } from "@/lib/fastapi";

type Params = { params: Promise<{ ruleId: string }> };

export async function POST(_request: Request, { params }: Params) {
  const { ruleId } = await params;
  return proxyFastApi(`/v1/maintenance/rules/${encodeURIComponent(ruleId)}/activate`, {
    method: "POST",
  });
}
