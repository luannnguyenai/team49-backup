"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Lock } from "lucide-react";

import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { authApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

const schema = z
  .object({
    new_password: z
      .string()
      .min(1, "Password is required"),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Password confirmation does not match",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export default function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    if (!token) return;
    setError(null);
    setIsLoading(true);
    try {
      await authApi.confirmPasswordReset({
        token,
        new_password: data.new_password,
      });
      router.push("/login?reset=success");
    } catch (err: unknown) {
      setError(getErrorMessage((err as { response?: { data?: unknown } })?.response?.data ?? err));
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 animate-fade-in">
          This reset link is invalid.
        </div>
        <Link href="/forgot-password" className="btn-secondary flex justify-center">
          Request a new reset link
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {error && (
        <div className="space-y-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 animate-fade-in">
          <p>{error}</p>
          <Link href="/forgot-password" className="link">
            Request a new reset link
          </Link>
        </div>
      )}

      <Input
        label="New password"
        type={showPassword ? "text" : "password"}
        autoComplete="new-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            className="hover:text-slate-600"
            aria-label={showPassword ? "Hide new password" : "Show new password"}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        error={errors.new_password?.message}
        {...register("new_password")}
      />

      <Input
        label="Confirm new password"
        type={showConfirm ? "text" : "password"}
        autoComplete="new-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowConfirm((v) => !v)}
            className="hover:text-slate-600"
            aria-label={showConfirm ? "Hide password confirmation" : "Show password confirmation"}
          >
            {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        error={errors.confirm_password?.message}
        {...register("confirm_password")}
      />

      <Button type="submit" loading={isLoading} className="w-full">
        Reset password
      </Button>
    </form>
  );
}
