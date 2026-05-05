"use client";
// components/auth/RegisterForm.tsx

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, User, Eye, EyeOff } from "lucide-react";

import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuthStore } from "@/stores/authStore";

const schema = z
  .object({
    full_name: z
      .string()
      .min(2, "Full name must be at least 2 characters")
      .max(255, "Full name is too long"),
    email: z.string().email("Invalid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/\d/, "Password must contain at least 1 number")
      .regex(/[a-zA-Z]/, "Password must contain at least 1 letter"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Password confirmation does not match",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const { register: registerUser, isLoading, error, clearError } = useAuthStore();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const passwordValue = watch("password", "");

  const passwordStrength = (() => {
    if (!passwordValue) return 0;
    let score = 0;
    if (passwordValue.length >= 8) score++;
    if (/\d/.test(passwordValue)) score++;
    if (/[a-zA-Z]/.test(passwordValue)) score++;
    if (/[^a-zA-Z0-9]/.test(passwordValue)) score++;
    return score;
  })();

  const strengthLabel = ["", "Weak", "Fair", "Good", "Strong"][passwordStrength];
  const strengthColor = ["", "bg-red-400", "bg-yellow-400", "bg-blue-400", "bg-green-400"][passwordStrength];

  const onSubmit = async (data: FormData) => {
    clearError();
    try {
      await registerUser({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      });
      const next = searchParams.get("next") ?? searchParams.get("from");
      router.push(next ? `/onboarding?next=${encodeURIComponent(next)}` : "/onboarding");
    } catch {
      // error set in store
    }
  };

  const next = searchParams.get("next") ?? searchParams.get("from");
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400 animate-fade-in">
          {error}
        </div>
      )}

      <Input
        label="Full name"
        type="text"
        autoComplete="name"
        placeholder="Jane Doe"
        leftElement={<User className="h-4 w-4" />}
        error={errors.full_name?.message}
        {...register("full_name")}
      />

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        leftElement={<Mail className="h-4 w-4" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <div>
        <Input
          label="Password"
          type={showPassword ? "text" : "password"}
          autoComplete="new-password"
          placeholder="••••••••"
          leftElement={<Lock className="h-4 w-4" />}
          rightElement={
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="hover:text-slate-600 dark:hover:text-slate-300"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          }
          error={errors.password?.message}
          {...register("password")}
        />
        {/* Password strength meter */}
        {passwordValue && (
          <div className="mt-2">
            <div className="flex gap-1">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                    i <= passwordStrength ? strengthColor : "bg-slate-200 dark:bg-slate-700"
                  }`}
                />
              ))}
            </div>
            <p className="mt-1 text-xs text-text-muted">
              Strength: <span className="font-medium">{strengthLabel}</span>
            </p>
          </div>
        )}
      </div>

      <Input
        label="Confirm password"
        type={showConfirm ? "text" : "password"}
        autoComplete="new-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowConfirm((v) => !v)}
            className="hover:text-slate-600 dark:hover:text-slate-300"
            aria-label={showConfirm ? "Hide password" : "Show password"}
          >
            {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        error={errors.confirm_password?.message}
        {...register("confirm_password")}
      />

      <Button type="submit" loading={isLoading} className="w-full mt-2">
        Create account
      </Button>

      <p className="text-center text-sm text-text-body">
        Already have an account?{" "}
        <Link href={loginHref} className="link">
          Sign in
        </Link>
      </p>
    </form>
  );
}
