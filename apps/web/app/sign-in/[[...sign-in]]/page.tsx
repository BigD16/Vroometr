import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return (
      <main className="auth-screen">
        <h1>Sign in</h1>
        <p>
          Add <code>NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> and{" "}
          <code>CLERK_SECRET_KEY</code> to the repo-root <code>.env</code>, then restart{" "}
          <code>npm run dev</code>.
        </p>
      </main>
    );
  }
  return (
    <main className="auth-screen">
      <SignIn />
    </main>
  );
}
