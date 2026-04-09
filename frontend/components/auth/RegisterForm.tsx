"use client";
// components/auth/RegisterForm.tsx

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, User, Eye, EyeOff } from "lucide-react";

import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useAuthStore } from "@/stores/authStore";

const schema = z
  .object({
    full_name: z
      .string()
      .min(2, "Họ tên phải ít nhất 2 ký tự")
      .max(255, "Họ tên quá dài"),
    email: z.string().email("Email không hợp lệ"),
    password: z
      .string()
      .min(8, "Mật khẩu phải ít nhất 8 ký tự")
      .regex(/\d/, "Mật khẩu phải chứa ít nhất 1 chữ số")
      .regex(/[a-zA-Z]/, "Mật khẩu phải chứa ít nhất 1 chữ cái"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Mật khẩu xác nhận không khớp",
    path: ["confirm_password"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterForm() {
  const router = useRouter();
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

  const strengthLabel = ["", "Yếu", "Trung bình", "Tốt", "Mạnh"][passwordStrength];
  const strengthColor = ["", "bg-red-400", "bg-yellow-400", "bg-blue-400", "bg-green-400"][passwordStrength];

  const onSubmit = async (data: FormData) => {
    clearError();
    try {
      await registerUser({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      });
      router.push("/onboarding");
    } catch {
      // error set in store
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-900/20 px-4 py-3 text-sm text-red-600 dark:text-red-400 animate-fade-in">
          {error}
        </div>
      )}

      <Input
        label="Họ và tên"
        type="text"
        autoComplete="name"
        placeholder="Nguyễn Văn A"
        leftElement={<User className="h-4 w-4" />}
        error={errors.full_name?.message}
        {...register("full_name")}
      />

      <Input
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="ban@example.com"
        leftElement={<Mail className="h-4 w-4" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <div>
        <Input
          label="Mật khẩu"
          type={showPassword ? "text" : "password"}
          autoComplete="new-password"
          placeholder="••••••••"
          leftElement={<Lock className="h-4 w-4" />}
          rightElement={
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="hover:text-slate-600 dark:hover:text-slate-300"
              aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
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
            <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              Độ mạnh: <span className="font-medium">{strengthLabel}</span>
            </p>
          </div>
        )}
      </div>

      <Input
        label="Xác nhận mật khẩu"
        type={showConfirm ? "text" : "password"}
        autoComplete="new-password"
        placeholder="••••••••"
        leftElement={<Lock className="h-4 w-4" />}
        rightElement={
          <button
            type="button"
            onClick={() => setShowConfirm((v) => !v)}
            className="hover:text-slate-600 dark:hover:text-slate-300"
            aria-label={showConfirm ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          >
            {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        error={errors.confirm_password?.message}
        {...register("confirm_password")}
      />

      <Button type="submit" loading={isLoading} className="w-full mt-2">
        Tạo tài khoản
      </Button>

      <p className="text-center text-sm" style={{ color: "var(--text-secondary)" }}>
        Đã có tài khoản?{" "}
        <Link href="/login" className="link">
          Đăng nhập
        </Link>
      </p>
    </form>
  );
}
