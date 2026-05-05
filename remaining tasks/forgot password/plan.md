# Forgot Password via Resend - Revised Implementation Plan

## Goal
Replace the current insecure direct password reset flow with a secure, email-token based reset flow using Resend.

Target UX:
- `/forgot-password`: user submits email only.
- `/reset-password?token=...`: user sets a new password from an emailed one-time link.
- Successful reset invalidates previously issued access/refresh tokens.
- API responses never reveal whether an email exists.

## Codebase Findings

### Current backend state
- `src/routers/auth.py` currently exposes `POST /api/auth/forgot-password` and directly resets a password from `{ email, new_password }`.
- `src/schemas/auth.py` currently defines `ForgotPasswordRequest` with `email` and `new_password`.
- `src/services/auth_service.py` currently contains `reset_password_for_email(db, email, new_password)` and updates the password immediately.
- `src/repositories/user_repo.py` only supports user lookup and password hash update.
- `src/models/user.py` has no `password_changed_at` or token-version field.
- `src/dependencies/auth.py` validates bearer tokens but does not reject tokens issued before a password reset.
- Login rate limiting exists in `src/routers/auth.py`; Redis sliding-window helper exists in `src/middleware/rate_limit.py`.
- No password reset token model/repository/service exists yet.
- `pyproject.toml` already includes `httpx`, so Resend can be called through the HTTP API without adding a Resend SDK dependency.

### Current frontend state
- `frontend/components/auth/ForgotPasswordForm.tsx` currently asks for email, new password, and confirmation on the forgot-password page.
- `frontend/app/(auth)/forgot-password/page.tsx` tells the user to enter email and a new password.
- `frontend/lib/api.ts` calls `POST /api/auth/forgot-password` with the current direct-reset payload.
- `frontend/types/index.ts` defines `ForgotPasswordPayload` with `email` and `new_password`.
- `frontend/app/(auth)/reset-password/page.tsx` does not exist.
- `frontend/middleware.ts` currently makes `/forgot-password` public, but not `/reset-password`.
- `frontend/components/auth/LoginForm.tsx` already has a `Forgot password?` link and should mostly stay unchanged.

### Existing tests to update
- `tests/test_auth_reset_password.py` currently asserts the insecure direct reset behavior and must be rewritten.
- `tests/test_auth_service_tokens.py` should be extended for token issue-time/session invalidation behavior.
- `tests/test_auth_dependency.py` should be extended to reject stale access tokens.
- Frontend auth tests exist under `frontend/tests/unit/auth/`; add reset-request/reset-confirm coverage there.

## Architecture Decisions
- Use DB-backed opaque reset tokens, not JWT reset links.
- Generate high-entropy random token with Python standard library.
- Store only a SHA-256 token hash in the database.
- Token TTL: 30 minutes by default.
- Token is single-use: set `used_at` after successful reset.
- Use `users.password_changed_at` for session invalidation.
- Use existing `httpx` dependency to call Resend API.
- Keep v1 mail send inline; no job queue.
- Keep the legacy `POST /api/auth/forgot-password` path removed or converted to reject the old direct-reset payload. New code should use `/request` and `/confirm` only.

## Public Interfaces

### `POST /api/auth/forgot-password/request`
Request:
```json
{ "email": "user@example.com" }
```
Response always uses the same success body for syntactically valid email input:
```json
{ "status": "ok" }
```
Rules:
- Normalize email before lookup/rate-limit keying.
- If account exists, create token and send reset email.
- If account does not exist, do not send email.
- Do not expose account existence.
- Rate limit by IP and normalized email.

### `POST /api/auth/forgot-password/confirm`
Request:
```json
{ "token": "opaque-token-from-email", "new_password": "NewPass456!" }
```
Response:
```json
{ "status": "ok" }
```
Rules:
- Reject invalid, expired, or used token.
- Hash and persist the new password.
- Mark reset token as used.
- Set `users.password_changed_at`.
- Existing access/refresh tokens issued before `password_changed_at` must stop working.

### Optional `POST /api/auth/forgot-password/validate`
Do not implement in v1 unless UI needs pre-validation before showing the form.
The reset page can instead submit `/confirm` and render backend failure states.

## Files Likely To Touch

### Backend
- `src/routers/auth.py`
- `src/schemas/auth.py`
- `src/services/auth_service.py`
- `src/services/password_reset_service.py` new
- `src/services/email_service.py` new
- `src/repositories/user_repo.py`
- `src/repositories/password_reset_repo.py` new
- `src/models/user.py`
- `src/models/password_reset.py` new
- `src/models/__init__.py`
- `src/dependencies/auth.py`
- `src/config.py`
- `alembic/versions/<new_revision>_add_password_reset_tokens.py` new

### Frontend
- `frontend/components/auth/ForgotPasswordForm.tsx`
- `frontend/components/auth/ResetPasswordForm.tsx` new
- `frontend/app/(auth)/forgot-password/page.tsx`
- `frontend/app/(auth)/reset-password/page.tsx` new
- `frontend/lib/api.ts`
- `frontend/types/index.ts`
- `frontend/middleware.ts`
- `frontend/components/auth/LoginForm.tsx` only if adding reset-success banner handling

### Tests
- `tests/test_auth_reset_password.py`
- `tests/test_auth_service_tokens.py`
- `tests/test_auth_dependency.py`
- new or existing frontend unit tests under `frontend/tests/unit/auth/`
- `frontend/tests/unit/middleware-public-routes.test.ts`

### Config/docs
- `.env.example`
- `README.md`
- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/PRODUCTION_CHECKLIST.md`

## Environment Variables
- `RESEND_API_KEY=`
- `EMAIL_FROM=`
- `FRONTEND_BASE_URL=http://localhost:3000`
- `PASSWORD_RESET_TOKEN_TTL_MINUTES=30`
- `RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=5`

## Phased Plan

### Phase 1 - Add password reset persistence schema
Task: Add DB schema for password reset tokens and password-change timestamp.

Implementation notes:
- Add `src/models/password_reset.py` with table `password_reset_tokens`.
- Add `users.password_changed_at` to `src/models/user.py`.
- Export `PasswordResetToken` from `src/models/__init__.py`.
- Add Alembic migration.
- Recommended token table fields:
  - `id`
  - `user_id`
  - `token_hash`
  - `expires_at`
  - `used_at`
  - `created_at`
  - `requested_ip`

DoD checklist:
- [ ] Alembic migration creates `password_reset_tokens`.
- [ ] Alembic migration adds nullable `users.password_changed_at`.
- [ ] `token_hash` is indexed or unique enough for efficient lookup.
- [ ] ORM model is importable through `src.models`.
- [ ] Downgrade reverses the new table/column where project convention supports downgrade.

Tests:
- [ ] Run `uv run pytest tests/test_alembic_heads.py`.
- [ ] Run `uv run pytest tests/test_auth_reset_password.py -q` after adding/adjusting model-level tests.
- [ ] Manual: run Alembic upgrade on local/test DB and verify new table + column exist.

### Phase 2 - Add password reset repository
Task: Add repository methods for reset-token CRUD.

Implementation notes:
- Add `src/repositories/password_reset_repo.py`.
- Required methods:
  - create token row
  - lookup by `token_hash`
  - mark token used
  - optionally revoke/consume all outstanding tokens for a user
- Keep DB access outside route handlers.

DoD checklist:
- [ ] Repository can create a reset token row.
- [ ] Repository can fetch token rows by hash.
- [ ] Repository can mark a token used atomically enough for v1.
- [ ] Repository does not store plaintext tokens.

Tests:
- [ ] Add unit tests with mocked session or DB-backed repository tests.
- [ ] Run `uv run pytest tests/test_auth_reset_password.py -q`.

### Phase 3 - Add reset token lifecycle service
Task: Add service logic for generating, hashing, validating, and consuming reset tokens.

Implementation notes:
- Add `src/services/password_reset_service.py`.
- Generate token with `secrets.token_urlsafe` or equivalent.
- Hash token with SHA-256 before storage/lookup.
- Validate states distinctly inside service: invalid, expired, used.
- Keep public request endpoint generic even when internal reason is known.

DoD checklist:
- [ ] Plaintext token is returned only once for email link creation.
- [ ] Database stores only token hash.
- [ ] Expired token cannot be used.
- [ ] Used token cannot be reused.
- [ ] Valid token can be consumed once.

Tests:
- [ ] Token hash test proves plaintext token is not persisted.
- [ ] Invalid token test.
- [ ] Expired token test.
- [ ] Used token test.
- [ ] Valid consume test.
- [ ] Run `uv run pytest tests/test_auth_reset_password.py -q`.

### Phase 4 - Add Resend email service
Task: Add a small email service that sends reset links through Resend.

Implementation notes:
- Add `src/services/email_service.py`.
- Use existing `httpx` dependency to call `https://api.resend.com/emails`.
- Read config from `src/config.py`.
- Build reset link with `FRONTEND_BASE_URL/reset-password?token=...`.
- In tests, mock the email service; do not call Resend.

DoD checklist:
- [ ] `RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_BASE_URL`, and token TTL settings exist in `src/config.py`.
- [ ] Email service sends subject/body with working reset link.
- [ ] Missing email config fails clearly in non-test usage.
- [ ] Tests mock network calls.
- [ ] No API key is logged.

Tests:
- [ ] Unit test reset link construction.
- [ ] Unit test Resend payload shape with mocked `httpx`.
- [ ] Run `uv run pytest tests/test_auth_reset_password.py -q`.

### Phase 5 - Implement reset request endpoint
Task: Replace direct reset request behavior with email-only reset request.

Implementation notes:
- Update `src/schemas/auth.py`:
  - `ForgotPasswordRequest` should contain email only or be renamed to `ForgotPasswordRequestBody`.
  - Add confirm schema separately later.
- Update `src/routers/auth.py`:
  - add `POST /api/auth/forgot-password/request`
  - stop accepting `new_password` on request
  - always return `{ "status": "ok" }` for syntactically valid email, whether user exists or not
- Add rate limiting by IP and normalized email.

DoD checklist:
- [ ] `POST /api/auth/forgot-password/request` accepts `{ email }`.
- [ ] Existing email returns `200 { status: "ok" }` and triggers email send.
- [ ] Unknown email returns `200 { status: "ok" }` and does not trigger email send.
- [ ] Request with `new_password` no longer performs a password change.
- [ ] Rate limiting can return `429`.

Tests:
- [ ] Rewrite old route tests that currently expect direct reset.
- [ ] Test existing email request triggers reset token creation/email send.
- [ ] Test unknown email request is generic and sends no email.
- [ ] Test old direct payload cannot update password.
- [ ] Test rate limit returns `429`.
- [ ] Run `uv run pytest tests/test_auth_reset_password.py tests/test_auth_rate_limit.py -q`.

### Phase 6 - Implement reset confirm endpoint
Task: Add endpoint that consumes a valid token and updates the password.

Implementation notes:
- Update `src/schemas/auth.py` with `ForgotPasswordConfirmRequest`.
- Add `POST /api/auth/forgot-password/confirm`.
- Move final password update into password reset service, not route code.
- Update `UserRepository.update_hashed_password` or add a method that also sets `password_changed_at`.

DoD checklist:
- [ ] Valid token updates password hash.
- [ ] Valid token sets `used_at`.
- [ ] Valid token sets `users.password_changed_at`.
- [ ] Invalid token returns a non-2xx error with safe message.
- [ ] Expired token returns a non-2xx error with safe message.
- [ ] Used token returns a non-2xx error with safe message.

Tests:
- [ ] Valid token happy path.
- [ ] Invalid token failure.
- [ ] Expired token failure.
- [ ] Used token failure.
- [ ] Old password fails after reset; new password succeeds.
- [ ] Run `uv run pytest tests/test_auth_reset_password.py -q`.

### Phase 7 - Invalidate stale access and refresh tokens
Task: Reject tokens issued before the user password was changed.

Implementation notes:
- `create_access_token` and `create_refresh_token` already include `iat`; ensure `TokenPayload` includes `iat` explicitly.
- Update `src/dependencies/auth.py` to reject access tokens whose `iat` is before `user.password_changed_at`.
- Update refresh endpoint in `src/routers/auth.py` to reject stale refresh tokens before issuing a new access token.
- Preserve existing token denylist behavior.

DoD checklist:
- [ ] Access token issued before reset is rejected.
- [ ] Refresh token issued before reset is rejected.
- [ ] Tokens issued after reset still work.
- [ ] Existing revoked-token behavior still works.

Tests:
- [ ] Add dependency test for stale access token.
- [ ] Add refresh endpoint test for stale refresh token.
- [ ] Add token payload decode test that asserts `iat` is present.
- [ ] Run `uv run pytest tests/test_auth_dependency.py tests/test_auth_service_tokens.py tests/test_auth_reset_password.py -q`.

### Phase 8 - Update frontend API contracts
Task: Update frontend types and API wrapper to use request/confirm endpoints.

Implementation notes:
- Update `frontend/types/index.ts`:
  - `ForgotPasswordPayload` should be `{ email: string }`.
  - Add `ResetPasswordPayload` with `{ token: string; new_password: string }`.
- Update `frontend/lib/api.ts`:
  - `authApi.requestPasswordReset(...)` posts `/api/auth/forgot-password/request`.
  - `authApi.confirmPasswordReset(...)` posts `/api/auth/forgot-password/confirm`.
  - Remove or stop using the old direct `forgotPassword` method.

DoD checklist:
- [ ] No frontend API call sends `new_password` to `/forgot-password/request`.
- [ ] Confirm API posts token and new password to `/confirm`.
- [ ] TypeScript types match backend schemas.

Tests:
- [ ] Run `npm --prefix frontend run type-check`.
- [ ] Add/update API unit test if existing pattern supports it.

### Phase 9 - Convert forgot-password UI to email-only request
Task: Make `/forgot-password` request only an email reset link.

Implementation notes:
- Update `frontend/components/auth/ForgotPasswordForm.tsx` to email-only.
- Remove password/confirm fields and eye toggle state from this form.
- Show generic success state: `If an account exists, we sent a reset link.`
- Do not redirect immediately to login after submit unless UX explicitly wants it; showing the generic success state is clearer.
- Update `frontend/app/(auth)/forgot-password/page.tsx` copy.

DoD checklist:
- [ ] Forgot-password form has only email field.
- [ ] Submit button says `Send reset link`.
- [ ] Success copy is generic.
- [ ] Error handling covers validation/rate-limit/network errors.
- [ ] Existing `next` preservation on login/register links is not broken.

Tests:
- [ ] Frontend unit test form submits only email.
- [ ] Frontend unit test generic success message appears.
- [ ] Frontend unit test password fields are absent on forgot-password page.
- [ ] Run `npm --prefix frontend test -- frontend/tests/unit/auth`.
- [ ] Run `npm --prefix frontend run type-check`.

### Phase 10 - Add reset-password UI
Task: Add `/reset-password?token=...` page and form.

Implementation notes:
- Add `frontend/app/(auth)/reset-password/page.tsx`.
- Add `frontend/components/auth/ResetPasswordForm.tsx`.
- Read token from query params.
- Validate password strength and confirmation client-side.
- Submit token + new password to confirm endpoint.
- On success, redirect to `/login?reset=success` or show a login CTA.
- Add `/reset-password` to `frontend/middleware.ts` public paths.

DoD checklist:
- [ ] Missing token state is handled.
- [ ] New password and confirm password fields exist.
- [ ] Weak password validation matches backend minimum policy.
- [ ] Mismatched confirmation shows inline error.
- [ ] Successful reset redirects or links to login with success context.
- [ ] Invalid/expired/used token failures show a safe message and CTA to request a new link.
- [ ] `/reset-password` is public in middleware.

Tests:
- [ ] Unit test missing token state.
- [ ] Unit test mismatched password validation.
- [ ] Unit test confirm API receives token and new password.
- [ ] Unit test invalid/expired/used backend errors render CTA.
- [ ] Unit test middleware allows unauthenticated `/reset-password`.
- [ ] Run `npm --prefix frontend test -- frontend/tests/unit/auth frontend/tests/unit/middleware-public-routes.test.ts`.
- [ ] Run `npm --prefix frontend run type-check`.

### Phase 11 - Add login reset-success feedback
Task: Show a success banner on login after reset completes.

Implementation notes:
- If reset page redirects to `/login?reset=success`, update `LoginForm` or login page to show `Password reset successfully. Please sign in again.`
- Keep existing login error rendering intact.

DoD checklist:
- [ ] Login page shows reset success message only for reset success query/state.
- [ ] Existing login validation and error display still work.
- [ ] Existing forgot-password link still works.

Tests:
- [ ] Unit test login success banner appears for reset success state.
- [ ] Unit test normal login page does not show reset success banner.
- [ ] Run `npm --prefix frontend test -- frontend/tests/unit/auth`.

### Phase 12 - Update environment and deployment docs
Task: Document required Resend and reset-flow configuration.

Implementation notes:
- Update `.env.example`.
- Update `README.md` for local setup.
- Update `deploy/ENVIRONMENT_MATRIX.md` and `deploy/PRODUCTION_CHECKLIST.md` if present and current.
- Document sender/domain verification in Resend.

DoD checklist:
- [ ] `.env.example` includes all new env vars with safe placeholders.
- [ ] README explains local reset email setup.
- [ ] Deploy docs mention production Resend domain verification and secret storage.
- [ ] No real secret values are committed.

Tests:
- [ ] Manual review changed docs for accidental secrets.
- [ ] Run `git diff -- .env.example README.md deploy/ENVIRONMENT_MATRIX.md deploy/PRODUCTION_CHECKLIST.md` before commit.

### Phase 13 - End-to-end verification pass
Task: Run final backend, frontend, and manual verification for the complete flow.

DoD checklist:
- [ ] Direct reset flow is gone.
- [ ] Request endpoint is generic for existing and unknown emails.
- [ ] Real or mocked Resend email contains a working reset link.
- [ ] Token is hashed at rest.
- [ ] Token expires.
- [ ] Token is single-use.
- [ ] Successful reset invalidates old access and refresh tokens.
- [ ] Old password no longer works.
- [ ] New password works.
- [ ] Frontend request and confirm flows are covered by tests.
- [ ] Config/docs are complete.

Automated tests:
- [ ] `uv run pytest tests/test_auth_reset_password.py tests/test_auth_service_tokens.py tests/test_auth_dependency.py tests/test_auth_rate_limit.py -q`
- [ ] `uv run pytest tests/test_alembic_heads.py -q`
- [ ] `npm --prefix frontend run type-check`
- [ ] `npm --prefix frontend test -- frontend/tests/unit/auth frontend/tests/unit/middleware-public-routes.test.ts`

Manual checks:
- [ ] Start backend and frontend locally.
- [ ] Open login page and click `Forgot password?`.
- [ ] Submit existing email; verify generic success message.
- [ ] Submit unknown email; verify same generic success message.
- [ ] Use captured/local test email link or mocked token to open `/reset-password?token=...`.
- [ ] Submit weak password; verify inline validation.
- [ ] Submit mismatched confirmation; verify inline validation.
- [ ] Submit valid new password; verify redirect/success banner on login.
- [ ] Try old password; verify login fails.
- [ ] Try new password; verify login succeeds.
- [ ] Reuse the same reset link; verify used/invalid state.
- [ ] Try an expired token; verify expired/invalid state.
- [ ] Try a protected API call with pre-reset access token; verify 401.
- [ ] Try refresh with pre-reset refresh token; verify 401.

## Implementation Order Rationale
1. Schema first because services and invalidation depend on persisted token/user fields.
2. Repository second to keep route/service code thin.
3. Token service before routes so security behavior is testable without HTTP.
4. Email service before request endpoint so `/request` can be completed in one pass.
5. Request endpoint before confirm endpoint because it produces tokens/links.
6. Invalidation after confirm because it depends on `password_changed_at` being set.
7. Frontend after backend contracts are stable.
8. Docs and end-to-end verification last.

## Out of Scope for v1
- Async job queue for email delivery.
- Multiple email templates/localization.
- Admin UI for reset tokens.
- Password history/reuse policy.
- Account lockout beyond request rate limiting.
