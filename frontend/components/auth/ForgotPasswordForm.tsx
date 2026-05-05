"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Mail } from "lucide-react";

import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { authApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

const schema = z.object({
  email: z.string().email("Invalid email address"),
});

type FormData = z.infer<typeof schema>;

export default function ForgotPasswordForm() {
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const next = searchParams.get("next") ?? searchParams.get("from");
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";

  const onSubmit = async (data: FormData) => {
    setError(null);
    setIsSubmitted(false);
    setIsLoading(true);
    try {
      await authApi.requestPasswordReset({ email: data.email });
      setIsSubmitted(true);
    } catch (err: unknown) {
      setError(getErrorMessage((err as { response?: { data?: unknown } })?.response?.data ?? err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {isSubmitted && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 animate-fade-in">
          If an account exists, we sent a reset link.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 animate-fade-in">
          {error}
        </div>
      )}

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        leftElement={<Mail className="h-4 w-4" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <Button type="submit" loading={isLoading} className="w-full">
        Send reset link
      </Button>

      <p className="text-center text-sm text-text-body">
        Remembered your password?{" "}
        <Link href={loginHref} className="link">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
