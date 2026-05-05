# Sync UI — Đồng Bộ Toàn Hệ Thống Theo Ngôn Ngữ Landing Page

## Bối Cảnh & Hướng Đi

Landing page đã có visual signature mạnh và được approve. Mục tiêu là kéo **toàn bộ app** (auth, protected, assessment, admin) về **cùng ngôn ngữ với Landing**, không phải ngược lại.

`redesign.md` Phase 1 (đã thực hiện) định nghĩa `.btn-primary = bg-primary-600` (cyan). Điều này **lệch khỏi Landing** — Landing dùng `bg-slate-950` (ink) cho primary CTA, cyan chỉ làm accent. Vì vậy plan này **redefine `.btn-primary` thành ink slate-950** và update các page bị lệch.

## Visual Signature Của Landing (Nguồn Chân Lý)

| Element | Class / Value |
|---|---|
| Page background | `bg-surface-page` + radial glow indigo/cyan |
| **Primary CTA** | `bg-slate-950 text-white rounded-full px-6 py-3 hover:bg-slate-800` → **INK** |
| **Secondary CTA** | `border-slate-200 bg-white/80 text-slate-700 rounded-full hover:bg-white` → **GLASS OUTLINE** |
| Section accent chip | `border-cyan-200/80 bg-white/70 text-cyan-700` (light) / `border-cyan-400/30 bg-slate-900/70 text-cyan-200` (dark) |
| Heading | `text-slate-950 dark:text-white` (font 4xl→6xl responsive) |
| Body text | `text-slate-600 dark:text-slate-200` |
| Bullet/check icon | `text-cyan-500` |
| Glass card | `rounded-3xl border-white/70 bg-white/70 backdrop-blur shadow-[0_20px_60px_-35px_rgba(15,23,42,0.35)]` |
| Ink showcase card | `rounded-[32px] bg-slate-950 text-white border-slate-200/80 shadow-[0_30px_80px_-40px_rgba(8,145,178,0.65)]` |
| Hero/icon gradient | `bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400` |
| Decorative glow | `bg-cyan-400/25 blur-3xl` |
| Card radius | `rounded-3xl` (audience), `rounded-[32px]` (showcase), `rounded-2xl` (icon box) |
| CTA radius | `rounded-full` |

## Hệ Quả: Token Cần Sửa

| Token / class | Cũ (Phase 1 redesign.md) | Mới (đồng bộ Landing) |
|---|---|---|
| `.btn-primary` | `bg-primary-600` (cyan) `rounded-lg` | `bg-brand-ink` (slate-950) `rounded-full` |
| `.btn-secondary` | `bg-surface-card border-border-subtle rounded-lg` | `bg-white/80 border-slate-200 rounded-full` (glass outline) |
| `--brand-ink` | có (`#020617`) nhưng chưa dùng làm CTA | promote thành CTA primary bg |
| `--brand-primary` (cyan) | dùng cho button | giữ nhưng chỉ cho **accent surface** (chip, icon, soft bg) |
| `.card` | `rounded-xl p-6 shadow-card` | giữ cho protected pages, **thêm `.card-glass` + `.card-ink`** cho hero/feature |
| `bg-surface-accent-soft` | `#ecfeff` | giữ — vẫn là cyan accent soft |

**Cyan KHÔNG biến mất** — nó vẫn là accent color (chip, link, bullet check, soft background). Chỉ là **không làm primary button bg** nữa.

## Cấu Trúc Phase (Đã Cập Nhật)

| Phase | Scope | Ưu tiên | DoD chính |
|---|---|---|---|
| [Phase 0](./phase-0-retint-buttons.md) | Re-tint `.btn-primary` → ink, `.btn-secondary` → glass outline. Cập nhật tailwind + test contract | 🔴 P0 | Mọi page đang dùng `.btn-primary` tự động chuyển sang ink |
| [Phase 1](./phase-1-public-cta-unify.md) | Migrate ad-hoc CTA (`bg-blue-600` ở assessment/results, button tự build ở quiz/module-test) về `.btn-primary` mới | 🔴 P0 | Không còn ad-hoc primary CTA bên ngoài `.btn-primary` |
| [Phase 2](./phase-2-auth-pages-refactor.md) | 3 file auth bỏ inline CSS var, dùng `.btn-primary` (ink) + `.input-base` + `text-text-strong` | 🟠 P1 | Auth pages match Landing — ink CTA, glass card frame |
| [Phase 3](./phase-3-decorative-tokens.md) | Định nghĩa decorative token: bloom, session-type, achievement-tier, insight, state, chart + `.card-glass`, `.card-ink` variants | 🟠 P1 | Token & utility wire xong, chưa migrate page |
| [Phase 4](./phase-4-bloom-session-migrate.md) | Migrate history/assessment/quiz/module-test/profile/dashboard/learning-path sang token decorative | 🟡 P2 | 0 raw hex / raw multi-hue tailwind trong `.tsx` |
| [Phase 5](./phase-5-admin-chart-palette.md) | Admin chart palette + KPI card đồng bộ ngôn ngữ Landing | 🟡 P2 | Admin pages có cùng ngôn ngữ với Landing |

**Mỗi phase = 1 task. Phase 0 trước Phase 1. Phase 4 phụ thuộc Phase 3.**

## Bảng So Sánh Trước / Sau (Ngôn Ngữ Đồng Bộ)

| Pillar | Trước | Sau |
|---|---|---|
| Primary CTA | 3 ngôn ngữ song song: `bg-slate-950` (landing), `bg-blue-600` (assessment), `bg-primary-600` cyan (`.btn-primary` cũ) | 1 ngôn ngữ: `.btn-primary` = `bg-slate-950 rounded-full` (ink) |
| Secondary CTA | mixed: glass / outline / `.btn-secondary` xám | `.btn-secondary` = `border-slate-200 bg-white/80 rounded-full` (glass outline) |
| Accent | cyan literal vs `bg-surface-accent-soft` rải rác | cyan **chỉ** ở accent chip + icon + soft surface, không trên CTA |
| Auth pages | inline `style={{ var(--…) }}` | semantic utility, ink CTA, glass card |
| Card | mixed: `.card rounded-xl`, `rounded-2xl`, `rounded-3xl`, glass tự build | 3 variant rõ: `.card` (protected), `.card-glass` (landing/feature hero), `.card-ink` (showcase) |
| Bloom palette | 2 nguồn độc lập: hex + raw tailwind | 1 nguồn: `bg-bloom-{level}-soft text-bloom-{level}` |
| Hero gradient | dùng đúng nhưng rải rác | tokenize thành `.hero-gradient` class |

## Nguyên Tắc

- **Đồng bộ với Landing là tiêu chuẩn**, không phải ngược lại. Landing không bị động vào (trừ rút gọn nếu duplicate utility).
- Cyan brand vẫn quan trọng — chỉ chuyển vai trò từ "primary button color" sang "accent color".
- Hero gradient `from-indigo-600 via-cyan-500 to-teal-400` giữ nguyên ở mọi hero.
- Status semantic (success/warning/error) giữ riêng.
- Light mode primary, dark mode parity.
- Không động backend / handler / route / fetch.

## Verify End-to-End

```bash
cd frontend
npm run type-check

# Test contracts (Phase 0–5)
npm test -- --run frontend/tests/unit/ui \
  frontend/tests/unit/landing \
  frontend/tests/unit/layout \
  frontend/tests/unit/auth \
  frontend/tests/unit/tokens \
  frontend/tests/unit/admin

npm run build

# Visual sweep light + dark:
# 1. Landing → giữ nguyên (baseline)
# 2. Public nav → CTA Sign up giống Create account của landing (ink rounded-full)
# 3. Login/Register → glass card frame + ink CTA, accent cyan link
# 4. Dashboard / Profile / History → ink CTA, decorative qua token
# 5. Assessment / Quiz / Module-test → ink CTA, bloom/state qua token
# 6. Admin → ink CTA, chart palette unified

npx lighthouse http://localhost:3000 --only-categories=accessibility --preset=desktop
```

## Decision Đã Lock

- ✅ **Primary CTA = ink (slate-950) + rounded-full** (theo Landing)
- ✅ **Cyan = accent**, không phải button bg
- ✅ Card protected giữ `.card` (rounded-xl) — vì đó là dạng dense/utility, khác hero
- ✅ Hero/feature surface dùng `.card-glass` hoặc `.card-ink` (rounded-3xl)

## Decision Còn Mở (Cần User Confirm Khi Bắt Đầu)

- Stat icon palette (dashboard/profile/history): **multi-hue có chủ đích** (Option A) hay **gộp về cyan accent + neutral** (Option B)?
- Achievement tier mapping: 4 tier (bronze/silver/gold/platinum) hay map theo achievement type cụ thể?
- Profile avatar gradient `from-violet-500 to-purple-600`: đổi sang `from-indigo-600 via-cyan-500 to-teal-400` (hero gradient) hay giữ riêng?

## Liên Kết

- Plan tổng audit: `C:\Users\vanhu\.claude\plans\ph-n-t-ch-m-m-u-elegant-lecun.md`
- Token foundation gốc: `redesign.md`
- Landing reference: `frontend/components/landing/LandingPage.tsx`
