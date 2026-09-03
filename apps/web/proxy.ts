import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

import { PUBLIC_ROUTE_PATTERNS } from "./lib/public-routes";

const clerkEnabled = Boolean(process.env.CLERK_SECRET_KEY);

const isPublicRoute = createRouteMatcher([...PUBLIC_ROUTE_PATTERNS]);

export default clerkEnabled
  ? clerkMiddleware(async (auth, req) => {
      if (!isPublicRoute(req)) {
        await auth.protect();
      }
    })
  : function passthrough() {
      return NextResponse.next();
    };

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/:path*",
  ],
};
