"use client";
// components/auth/LoginForm.tsx

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, Eye, EyeOff } from "lucide-react";

import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuthStore } from "@/stores/authStore";

const schema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type FormData = z.infer<typeof schema>;

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const { login, isLoading, error, clearError } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    clearError();
    try {
      await login(data);
      const next = searchParams.get("next") ?? searchParams.get("from") ?? "/dashboard";
      router.push(next);
    } catch {
      // error is set in store
    }
  };

  const next = searchParams.get("next") ?? searchParams.get("from");
  const resetSuccess = searchParams.get("reset") === "success";
  const registerHref = next ? `/register?next=${encodeURIComponent(next)}` : "/register";
  const forgotPasswordHref = next ? `/forgot-password?next=${encodeURIComponent(next)}` : "/forgot-password";

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      {/* Global API error */}
      {resetSuccess && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 animate-fade-in">
          Password reset successfully. Please sign in again.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400 animate-fade-in">
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

      <Input
        label="Password"
        type={showPassword ? "text" : "password"}
        autoComplete="current-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            className="hover:text-slate-600 dark:hover:text-slate-300"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        }
        error={errors.password?.message}
        {...register("password")}
      />

      <div className="flex justify-end">
        <Link href={forgotPasswordHref} className="link text-sm">
          Forgot password?
        </Link>
      </div>

      <Button type="submit" loading={isLoading} className="w-full">
        Sign in
      </Button>

      <p className="text-center text-sm text-text-body">
        Don&apos;t have an account?{" "}
        <Link href={registerHref} className="link">
          Sign up now
        </Link>
      </p>
    </form>
  );
}
