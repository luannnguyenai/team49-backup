# Phase 2 — Refactor Auth Pages Bỏ Inline CSS Variable

**Ưu tiên:** 🟠 P1
**Phụ thuộc:** **Phase 0** (cần `.btn-primary` ink, `.btn-secondary` glass, `.card-glass` đã sẵn)
**Thời lượng ước tính:** 1–1.5 giờ

> **Ngôn ngữ đích:** Auth page nên cảm giác như "đứng cùng" với Landing — card glass nhẹ, heading ink đậm, primary CTA ink rounded-full, accent cyan ở link "Forgot password". Không phải card flat mặc định cũ.

## Vấn Đề

3 file auth bypass token Tailwind layer, dùng `style={{ ... var(--...) }}` inline ở >30 chỗ. Điều này:
- Không tuân thủ pattern semantic utility (`text-text-strong`, `bg-surface-card`).
- Không hỗ trợ purge hoặc IDE intellisense.
- Lệch khỏi style của các page protected khác.

| File | Số inline `style` |
|---|---|
| `frontend/app/(auth)/login/page.tsx` | nhiều |
| `frontend/app/(auth)/register/page.tsx` | nhiều |
| `frontend/app/(auth)/forgot-password/page.tsx` | nhiều |

## Files Cần Touch

- `frontend/app/(auth)/login/page.tsx`
- `frontend/app/(auth)/register/page.tsx`
- `frontend/app/(auth)/forgot-password/page.tsx`
- `frontend/tests/unit/auth/auth-pages-theme.test.tsx` *(mới)*

## Mapping Inline → Utility

| Inline hiện tại | Tailwind utility tương đương |
|---|---|
| `style={{ color: "var(--text-primary)" }}` | `text-text-strong` |
| `style={{ color: "var(--text-secondary)" }}` | `text-text-body` |
| `style={{ color: "var(--text-muted)" }}` | `text-text-muted` |
| `style={{ background: "var(--bg-page)" }}` | `bg-surface-page` |
| `style={{ background: "var(--bg-card)" }}` | `bg-surface-card` |
| `style={{ borderColor: "var(--border)" }}` | `border-border-subtle` |
| Custom button `style` | `.btn-primary` / `.btn-secondary` |
| Custom input `style` | `.input-base` |
| Label custom | `.label` |

## Scope

**Không động:**
- Form schema, react-hook-form, validation
- API call (`authApi.login`, `register`…)
- Routing redirect logic
- Field name / placeholder / error message text

**Chỉ refactor:** className + xóa `style={{}}` inline khi có utility tương đương.

## Implementation

### Pattern Mẫu — Login

```tsx
// Before
<div style={{ background: "var(--bg-card)" }} className="w-full max-w-md rounded-2xl border p-8 shadow-lg">
  <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
    Welcome back 👋
  </h2>
  <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
    Đăng nhập để tiếp tục học
  </p>
  <input
    style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    className="mt-4 w-full rounded-lg border px-3 py-2"
  />
  <button className="..." style={{ background: "var(--brand-primary)" }}>
    Đăng nhập
  </button>
</div>

// After — ngôn ngữ Landing: glass card + ink CTA
<div className="card-glass w-full max-w-md">
  <h2 className="text-xl font-semibold text-text-strong">Welcome back 👋</h2>
  <p className="mt-1 text-sm text-text-body">Đăng nhập để tiếp tục học</p>
  <input className="input-base mt-4" />
  <button className="btn-primary w-full mt-4">Đăng nhập</button>
  <Link href="/forgot-password" className="link mt-3 text-sm text-cyan-700 dark:text-cyan-300">
    Forgot password?
  </Link>
</div>
```

### Áp Dụng Cho 3 File

Lặp pattern trên cho:
1. `login/page.tsx`
2. `register/page.tsx`
3. `forgot-password/page.tsx`

Sau khi refactor: `grep -n 'style={{' frontend/app/\(auth\)/` phải về **0 match** (trừ trường hợp inline-style buộc phải có như dynamic gradient — hiếm trong auth).

## DoD Checklist

- [ ] 3 file auth không còn inline `style={{ ... var(--...) }}` (trừ trường hợp dynamic không thay được)
- [ ] Heading dùng `text-text-strong`
- [ ] Subtext dùng `text-text-body` / `text-text-muted`
- [ ] Container card dùng `.card` hoặc `bg-surface-card border-border-subtle`
- [ ] Input dùng `.input-base`
- [ ] Submit button dùng `.btn-primary`
- [ ] Secondary action (Forgot password link, Cancel) dùng `.btn-ghost` hoặc `.link`
- [ ] Form behavior giữ nguyên: submit, validation, redirect đều OK
- [ ] Type check pass
- [ ] Unit test mới pass
- [ ] E2E manual: login thành công, register thành công, forgot password gửi email
- [ ] Dark mode parity: 3 page render đúng ở dark
- [ ] Commit: `design(sync-ui): refactor auth pages to semantic utilities`

## Unit Tests

### `frontend/tests/unit/auth/auth-pages-theme.test.tsx`

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoginPage from "@/app/(auth)/login/page";
import RegisterPage from "@/app/(auth)/register/page";
import ForgotPasswordPage from "@/app/(auth)/forgot-password/page";

describe("Auth pages theme contract", () => {
  it.each([
    ["login", LoginPage],
    ["register", RegisterPage],
    ["forgot-password", ForgotPasswordPage],
  ])("%s page does not use inline CSS var styles", (_name, Page) => {
    const { container } = render(<Page />);
    const inlineVarUsage = container.querySelectorAll('[style*="var(--"]');
    expect(inlineVarUsage.length).toBe(0);
  });

  it.each([
    ["login", LoginPage],
    ["register", RegisterPage],
    ["forgot-password", ForgotPasswordPage],
  ])("%s page renders submit button with btn-primary", (_name, Page) => {
    const { container } = render(<Page />);
    const primary = container.querySelector("button.btn-primary, button[class*='btn-primary']");
    expect(primary).toBeTruthy();
  });
});
```

## Verify

```bash
cd frontend
npm run type-check
npm test -- --run frontend/tests/unit/auth/auth-pages-theme.test.tsx

# Grep guard - không nên còn inline var trên auth pages
grep -rn 'style={{.*var(--' frontend/app/\(auth\)/  # expect: empty

# Manual E2E:
npm run dev
# 1. /login: nhập sai → thấy error styled đúng
# 2. /login: nhập đúng → redirect dashboard
# 3. /register: tạo tài khoản mới
# 4. /forgot-password: submit email
# 5. Toggle dark mode trên cả 3 page
```

## Rollback

```bash
git revert <commit-sha>
```
