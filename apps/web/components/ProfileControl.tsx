"use client";

import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";

export function ProfileControl() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (!clerkEnabled) {
    return (
      <button type="button" className="profile" disabled>
        <span>?</span>
        <div>
          <b>Sign in</b>
          <small>Add Clerk keys</small>
        </div>
      </button>
    );
  }
  return (
    <>
      <Show when="signed-out">
        <div className="auth-controls">
          <SignInButton>
            <button type="button" className="profile">
              <span>IN</span>
              <div>
                <b>Sign in</b>
                <small>Clerk</small>
              </div>
            </button>
          </SignInButton>
          <SignUpButton>
            <button type="button" className="auth-text-btn">
              Sign up
            </button>
          </SignUpButton>
        </div>
      </Show>
      <Show when="signed-in">
        <div className="profile profile-signed-in">
          <UserButton />
        </div>
      </Show>
    </>
  );
}
