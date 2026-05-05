# Forgot Password + Resend Setup Guide

This app uses Resend to send password reset links. The password reset flow is email-token based; users never set a new password directly from the forgot-password request screen.

## Required external service

Required:
- Resend account
- Resend API key
- Verified sender identity or domain in Resend

Optional but recommended for production:
- Redis, already supported by the app, for distributed forgot-password rate limiting across backend workers

No background worker or queue is required in v1. The backend sends the Resend email inline during the reset request.

## Environment variables

Backend variables:

```env
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@your-verified-domain.com
FRONTEND_BASE_URL=http://localhost:3000
PASSWORD_RESET_TOKEN_TTL_MINUTES=30
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=5
```

Local defaults:

```env
FRONTEND_BASE_URL=http://localhost:3000
PASSWORD_RESET_TOKEN_TTL_MINUTES=30
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=5
```

Production example:

```env
FRONTEND_BASE_URL=https://your-frontend-domain.com
EMAIL_FROM=noreply@your-verified-domain.com
```

Never commit a real `RESEND_API_KEY`.

## Resend setup

1. Create or log in to a Resend account.
2. Add and verify a sender domain or sender identity.
3. Create an API key for email sending.
4. Set `RESEND_API_KEY` in the backend runtime environment.
5. Set `EMAIL_FROM` to an address allowed by the verified Resend sender/domain.
6. Set `FRONTEND_BASE_URL` to the public URL where users open reset links.
7. Restart/redeploy the backend after changing environment variables.

## Password reset flow

### 1. User requests a reset link

User opens the login page and clicks `Forgot password?`.

Frontend route:

```text
/forgot-password
```

The page asks for email only and submits:

```http
POST /api/auth/forgot-password/request
```

Payload:

```json
{ "email": "user@example.com" }
```

Backend behavior:
- Validates and normalizes the email.
- Rate limits by client IP and normalized email.
- If the account exists, creates a high-entropy opaque reset token.
- Stores only the SHA-256 token hash in `password_reset_tokens`.
- Sets an expiry using `PASSWORD_RESET_TOKEN_TTL_MINUTES`.
- Sends a Resend email containing a link to `/reset-password?token=...`.
- If the account does not exist, sends no email.

Response is always generic for valid email syntax:

```json
{ "status": "ok" }
```

Frontend success text is also generic:

```text
If an account exists, we sent a reset link.
```

This avoids leaking whether an email address has an account.

### 2. User clicks the emailed reset link

The email link points to:

```text
{FRONTEND_BASE_URL}/reset-password?token=<opaque-token>
```

Frontend route:

```text
/reset-password?token=...
```

The reset page reads the token from the query string and shows:
- New password
- Confirm new password

Client-side validation checks:
- minimum 8 characters
- at least one number
- at least one letter
- password confirmation matches

### 3. User confirms the new password

Frontend submits:

```http
POST /api/auth/forgot-password/confirm
```

Payload:

```json
{
  "token": "opaque-token-from-email",
  "new_password": "NewPass456!"
}
```

Backend behavior:
- Hashes the raw token with SHA-256.
- Finds the reset-token row by hash.
- Rejects invalid, expired, or already-used tokens.
- Hashes and saves the new password.
- Marks outstanding reset tokens for that user as used.
- Sets `users.password_changed_at`.

Success response:

```json
{ "status": "ok" }
```

The frontend redirects to:

```text
/login?reset=success
```

The login page shows:

```text
Password reset successfully. Please sign in again.
```

### 4. Old sessions are invalidated

Access and refresh JWTs include `iat` issued-at timestamps.

After password reset, the backend compares token `iat` with `users.password_changed_at`:
- tokens issued before the password change are rejected with `401`
- users must sign in again with the new password

## Failure states

| Case | Backend result | User-facing behavior |
|---|---|---|
| Unknown email on request | `200 { "status": "ok" }` | Same generic success message |
| Too many requests | `429` | Ask user to try again later |
| Missing token | No confirm call | Show invalid link and CTA to request a new link |
| Invalid token | `400` | Show invalid link and CTA |
| Expired token | `400` | Show expired link and CTA |
| Used token | `400` | Show already-used link and CTA |

## Verification checklist

Backend:

```bash
uv run pytest tests/test_auth_reset_password.py tests/test_auth_service_tokens.py tests/test_auth_dependency.py tests/test_auth_rate_limit.py -q
uv run pytest tests/test_alembic_heads.py -q
```

Frontend:

```bash
npm --prefix frontend run type-check
npm --prefix frontend test -- frontend/tests/unit/auth frontend/tests/unit/middleware-public-routes.test.ts
```

Manual:
- Submit an existing email from `/forgot-password`; verify a reset email is sent.
- Submit an unknown email; verify the same generic success message.
- Open `/reset-password?token=...` from the email.
- Submit a weak password; verify inline validation.
- Submit mismatched confirmation; verify inline validation.
- Submit a valid password; verify redirect to login success banner.
- Verify old password fails and new password succeeds.
- Reuse the same reset link; verify it is rejected.
- Use an old access or refresh token after reset; verify `401`.
