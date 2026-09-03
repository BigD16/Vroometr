/**
 * Paths reachable without a Clerk session.
 *
 * Middleware is a UX gate only. FastAPI still authorizes `/v1/*`.
 * `/api/*` stays public here so the Next.js BFF can return 401 JSON
 * instead of Clerk's unauthenticated 404.
 */
export const PUBLIC_ROUTE_PATTERNS = [
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api(.*)",
] as const;

export function isPublicPath(pathname: string): boolean {
  const path = pathname.split("?")[0] ?? pathname;
  return (
    path === "/sign-in" ||
    path.startsWith("/sign-in/") ||
    path === "/sign-up" ||
    path.startsWith("/sign-up/") ||
    path === "/api" ||
    path.startsWith("/api/")
  );
}
