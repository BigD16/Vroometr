"use client";

import { Show, UserButton } from "@clerk/nextjs";
import Link from "next/link";

import { mockUser } from "@/lib/mock-machine";

function MockProfile({ href }: { href?: string }) {
  const inner = (
    <>
      <span>{mockUser.initials}</span>
      <div>
        <b>{mockUser.displayName}</b>
        <small>{mockUser.planLabel}</small>
      </div>
      <em>⌄</em>
    </>
  );
  if (href) {
    return (
      <Link href={href} className="profile">
        {inner}
      </Link>
    );
  }
  return (
    <button type="button" className="profile">
      {inner}
    </button>
  );
}

export function ProfileControl() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (!clerkEnabled) {
    return <MockProfile />;
  }
  return (
    <>
      <Show when="signed-out">
        <MockProfile href="/sign-in" />
      </Show>
      <Show when="signed-in">
        <div className="profile profile-signed-in">
          <UserButton />
        </div>
      </Show>
    </>
  );
}
