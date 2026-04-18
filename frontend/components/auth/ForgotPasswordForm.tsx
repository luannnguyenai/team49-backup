"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";

import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { authApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

const schema = z
  .object({
    email: z.string().email("Email không hợp lệ"),
    new_password: z
      .string()
      .min(8, "Mật khẩu phải ít nhất 8 ký tự")
      .regex(/\d/, "Mật khẩu phải chứa ít nhất 1 chữ số")
      .regex(/[a-zA-Z]/, "Mật khẩu phải chứa ít nhất 1 chữ cái"),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Mật khẩu xác nhận không khớp",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export default function ForgotPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const next = searchParams.get("next") ?? searchParams.get("from");
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";

  const onSubmit = async (data: FormData) => {
    setError(null);
    setIsLoading(true);
    try {
      await authApi.forgotPassword({
        email: data.email,
        new_password: data.new_password,
      });
      router.push(loginHref);
    } catch (err: unknown) {
      setError(getErrorMessage((err as { response?: { data?: unknown } })?.response?.data ?? err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 animate-fade-in">
          {error}
        </div>
      )}

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="ban@example.com"
        leftElement={<Mail className="h-4 w-4" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <Input
        label="Mật khẩu mới"
        type={showPassword ? "text" : "password"}
        autoComplete="new-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            className="hover:text-slate-600 dark:hover:text-slate-300"
            aria-label={showPassword ? "Ẩn mật khẩu mới" : "Hiện mật khẩu mới"}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        error={errors.new_password?.message}
        {...register("new_password")}
      />

      <Input
        label="Xác nhận mật khẩu mới"
        type={showConfirm ? "text" : "password"}
        autoComplete="new-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowConfirm((v) => !v)}
            className="hover:text-slate-600 dark:hover:text-slate-300"
            aria-label={showConfirm ? "Ẩn xác nhận mật khẩu" : "Hiện xác nhận mật khẩu"}
          >
            {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        error={errors.confirm_password?.message}
        {...register("confirm_password")}
      />

      <Button type="submit" loading={isLoading} className="w-full">
        Đổi mật khẩu
      </Button>

      <p className="text-center text-sm" style={{ color: "var(--text-secondary)" }}>
        Nhớ mật khẩu rồi?{" "}
        <Link href={loginHref} className="link">
          Quay lại đăng nhập
        </Link>
      </p>
    </form>
  );
}
