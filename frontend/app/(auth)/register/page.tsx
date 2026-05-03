// app/(auth)/register/page.tsx

import { Suspense } from "react";
import type { Metadata } from "next";
import AuthBackLink from "@/components/auth/AuthBackLink";
import RegisterForm from "@/components/auth/RegisterForm";

export const metadata: Metadata = { title: "Sign Up" };

export default function RegisterPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          Create your account ✨
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Free to start. No credit card required.
        </p>
      </div>
      <Suspense>
        <RegisterForm />
      </Suspense>
      <AuthBackLink />
    </>
  );
}
