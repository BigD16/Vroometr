import "server-only";

import { auth } from "@clerk/nextjs/server";

export async function proxyFastApi(path: string, init?: RequestInit): Promise<Response> {
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

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);

  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
    return new Response(response.status === 204 ? null : await response.text(), {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (error) {
    console.error("FastAPI proxy request failed", { path, error });
    return Response.json(
      { error: { code: "api_unavailable", message: "Vroometr API is unavailable" } },
      { status: 502 },
    );
  }
}
