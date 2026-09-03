import { auth } from "@clerk/nextjs/server";

export async function GET() {
  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return Response.json(
      { error: { code: "misconfigured", message: "API_URL is not set" } },
      { status: 503 },
    );
  }
  const session = await auth();
  const token = await session.getToken();
  if (!token) {
    return Response.json(
      { error: { code: "unauthenticated", message: "Sign in required" } },
      { status: 401 },
    );
  }
  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/v1/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return new Response(await response.text(), {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
