# Feature: Auth Password Reset

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `2. Kiến trúc ứng dụng`, `4. Backend architecture`

## 1. Mục tiêu
Password reset cho phép user lấy lại quyền truy cập tài khoản thông qua email token-based flow, đồng thời giữ generic response, rate limiting, và token invalidation để tránh abuse.

## 2. User/problem this solves
Người dùng quên mật khẩu là trường hợp vận hành bắt buộc. Flow này phải giải quyết:
- reset mật khẩu mà không cần support thủ công;
- không để lộ account enumeration;
- không để spam email reset;
- thu hồi token cũ sau khi password đã đổi.

## 3. System scope
Backend:
- `src/routers/auth.py`
- `src/services/password_reset_service.py`
- `src/services/email_service.py`
- `src/repositories/password_reset_repo.py`
- `src/schemas/auth.py`

Frontend:
- `frontend/app/(auth)/forgot-password/page.tsx`
- `frontend/app/(auth)/reset-password/page.tsx`
- `frontend/components/auth/ForgotPasswordForm.tsx`
- `frontend/components/auth/ResetPasswordForm.tsx`

Tables/runtime:
- `users`
- `password_reset_tokens`
- Redis keys cho rate limit

## 4. Architecture & flow

```text
/forgot-password
  -> POST /api/auth/forgot-password/request
  -> check rate limit theo IP + email
  -> nếu account tồn tại: tạo opaque token
  -> gửi email qua Resend
  -> trả generic success response

/reset-password?token=...
  -> POST /api/auth/forgot-password/confirm
  -> validate token + expiry + used state
  -> đổi hashed password
  -> mark các token outstanding là used
  -> invalidate phiên auth liên quan qua password_changed_at
```

## 5. Key components
- `password_reset_service`: token issue/consume.
- `email_service`: gửi reset email.
- Redis rate limiting trong `auth.py`.
- Frontend auth pages giữ `next` param và generic UX messages.

## 6. Data model / contracts
Endpoints:
- `POST /api/auth/forgot-password/request`
- `POST /api/auth/forgot-password/confirm`

Dữ liệu cần đảm bảo:
- token entropy cao
- có TTL
- có trạng thái `used`
- `users.password_changed_at` được cập nhật

Response request phải generic để không cho phép đoán email có tồn tại hay không.

## 7. Technical decisions
- Gửi email inline qua Resend, không cần queue/worker ở v1.
- Rate limit theo cả IP và email.
- Dùng opaque token thay vì để user tự đặt password mới ở bước request.
- Sau reset, compare token `iat` với `password_changed_at` để vô hiệu hóa phiên cũ.

## 8. Risks / trade-offs
- Gửi email inline làm request path phụ thuộc email provider latency.
- Generic response tốt cho security nhưng khó debug hơn với user support.
- Cần quản lý sender domain/Resend config đúng môi trường.
- Nếu rate limit quá chặt sẽ ảnh hưởng user hợp lệ; quá lỏng lại dễ bị abuse.

## 9. Testing / validation
Backend:
- `tests/test_auth_reset_password.py`
- `tests/test_auth_rate_limit.py`
- `tests/test_auth_logout.py`

Frontend:
- `frontend/tests/unit/auth/password-reset-flow.test.tsx`
- `frontend/tests/unit/auth/form-next.test.tsx`
- `frontend/tests/unit/middleware-public-routes.test.ts`

Docs:
- `docs/forgot-password-resend.md`

## 10. Demo-worthy points
- Dù nhỏ hơn các feature adaptive, đây là một ví dụ tốt cho production hygiene.
- Có thể đưa vào report như một feature "security and account recovery".
- Thể hiện được backend contract, Redis rate limit, email integration, và auth UX thống nhất.
