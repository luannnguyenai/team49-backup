// app/(auth)/login/page.tsx

import { Suspense } from "react";
import type { Metadata } from "next";
import AuthBackLink from "@/components/auth/AuthBackLink";
import LoginForm from "@/components/auth/LoginForm";

export const metadata: Metadata = { title: "Sign In" };

export default function LoginPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-text-strong">
          Welcome back 👋
        </h2>
        <p className="mt-1 text-sm text-text-body">
          Sign in to continue your learning journey.
        </p>
      </div>
      <Suspense>
        <LoginForm />
      </Suspense>
      <AuthBackLink />
    </>
  );
}
