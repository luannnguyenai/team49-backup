# Đánh Giá Plan `sync-ui` — Có Đồng Bộ Được Về Ngôn Ngữ Landing Không?

## Context

Plan `sync-ui` (Phase 0–5) đặt mục tiêu kéo toàn bộ app (auth, protected, assessment, admin) về cùng ngôn ngữ visual của Landing Page: **Primary CTA = ink (slate-950) rounded-full**, **Secondary = glass outline rounded-full**, **cyan chỉ làm accent**. File này verify plan có khớp current state codebase không và có đủ để đạt mục tiêu đồng bộ không.

## Tóm Tắt Verdict

**Plan tốt, có cấu trúc, đúng hướng — nhưng có 4 điểm cần điều chỉnh trước khi execute.**

| Phase | Verdict | Note |
|---|---|---|
| Phase 0 | ✅ **ĐÃ THỰC HIỆN** | `globals.css` & `tailwind.config.ts` đã có `--brand-ink`, `.btn-primary` → ink rounded-full, `.btn-secondary` → glass, `.card-glass`, `.card-ink`. Plan này nên **mark DONE**, chỉ cần verify test contract đã update. |
| Phase 1 | 🟡 **CẦN ĐIỀU CHỈNH** | Giả định `bg-blue-600` / `bg-emerald-600` là primary CTA chưa chính xác — chúng đang là badge color cho Bloom/difficulty/mastery, không phải button. Cần re-scope. |
| Phase 2 | ✅ **OK** | Auth pages còn 2 inline `style={{ var(--…) }}` mỗi file — scope nhỏ, mapping rõ. Khả thi 1–1.5h. |
| Phase 3 | ✅ **OK** | Token bloom/session/tier/state/chart chưa có trong tailwind.config — cần thêm đúng như plan. |
| Phase 4 | ✅ **OK** | Đã verify `TYPE_COLORS`, `BLOOM_BAR_COLOR`, `BLOOM_BADGE`, achievement borders tồn tại đúng như plan mô tả. |
| Phase 5 | ✅ **OK** | Recharts là chart lib; `lib/admin/chart-theme.ts` chưa có — đúng scope plan. |

## Điều Đã Verify Đúng

1. **Landing baseline khớp 100%** — `LandingPage.tsx` line 98–110: 2 CTA đúng `rounded-full bg-slate-950 hover:bg-slate-800` và `border-slate-200 bg-white/80 rounded-full`. Plan chọn đúng nguồn chân lý.
2. **Phase 0 đã commit một phần** — `globals.css` (M trong git) đã có:
   - `--brand-ink`, `--brand-ink-hover`, `--brand-ink-fg`
   - `--glass-bg`, `--glass-border`, `--glass-fg`
   - `.btn-primary` resolve `var(--brand-ink)` + `rounded-full`
   - `.btn-secondary` glass + `rounded-full` + `backdrop-filter: blur(8px)`
   - `.card-glass` (line 118–127), `.card-ink` (line 130–140)
   - `tailwind.config.ts`: `brand.ink*`, `glass.*` đã map.
3. **PublicTopNav** — đã dùng `rounded-full bg-slate-950` cho Sign up — đã đồng bộ.
4. **Auth pages** vẫn còn `style={{ color: "var(--text-primary)" }}` — đúng đối tượng Phase 2.
5. **Decorative palette** vẫn raw — `TYPE_COLORS`, `BLOOM_BAR_COLOR` (hex), `BLOOM_BADGE` (sky/violet/amber/rose), achievement (`border-blue-400` etc.) — đúng đối tượng Phase 4.

## 4 Điểm Cần Điều Chỉnh Trước Khi Execute

### 1. Phase 0 cần re-classify thành "verify-only"

`globals.css` & `tailwind.config.ts` đã modified. Phase 0 không còn là task implement, mà là task **verify**:
- Diff `globals.css` & `tailwind.config.ts` xem có match đúng spec plan không.
- Update `frontend/tests/unit/ui/button-theme.test.tsx` để assert `.btn-primary` → ink (chứ không phải cyan).
- Visual sweep các page sẵn có dùng `.btn-primary` xem có vỡ không.

### 2. Phase 1 cần re-scope quan trọng

Plan hiện liệt kê "Quiz `bg-emerald-600`, Module-test `bg-emerald-600`, Assessment results `bg-blue-600`" như là ad-hoc primary CTA — **đây là giả định sai**:

- `quiz/page.tsx` lines 37–54: `BLOOM_COLORS`, `DIFF_COLORS` là **badge color** (bg-100 + text-700), không phải button.
- `assessment/results/page.tsx` lines 34–43: `MASTERY_CONFIG.proficient = "text-blue-600"` là **mastery indicator color**, không phải CTA. Line 90 `bg-emerald-600` là **toast success**, không phải primary action.
- Landing `LandingPage.tsx`, `PublicTopNav.tsx` đã dùng `rounded-full bg-slate-950` literal — sau Phase 1 sẽ refactor sang `.btn-primary` để đỡ duplicate.

→ **Action:** Re-grep cụ thể trên 5 file để tìm primary action button thực sự (Submit, Continue, Next), không phải badge/toast/mastery indicator. Có thể Phase 1 chỉ còn 2 file (Landing + PublicTopNav refactor sang class) thay vì 5.

### 3. Decision points trong README chưa được lock trước khi vào Phase 4

3 quyết định mở:
- Stat icon palette: multi-hue (Option A) hay đồng nhất (Option B)?
- Achievement tier mapping cụ thể (4 tier hay theo type)?
- Profile avatar gradient: hero gradient hay riêng?

→ **Action:** Phải user confirm trước khi Phase 3 finalize token list (vì Option A cần `--stat-courses`, `--stat-time`… mà plan Phase 3 hiện không có). Nếu chọn A, **Phase 3 phải thêm stat token group**.

### 4. Test contract risk: JSDOM không apply Tailwind

Plan Phase 0/3 nhắc `getComputedStyle` test có thể fail do JSDOM không nạp Tailwind compiled CSS. Plan đã ghi note "skip nếu setup JSDOM không nạp được" — nhưng nên **chốt trước**: test chỉ assert class name, không assert computed style. Visual contract test chuyển sang Playwright nếu cần đảm bảo render thật.

## Đánh Giá Khả Năng Đạt Mục Tiêu Đồng Bộ

| Tiêu chí đồng bộ | Plan có giải quyết? |
|---|---|
| Mọi primary CTA cùng ngôn ngữ ink rounded-full | ✅ Phase 0 + Phase 1 |
| Mọi secondary CTA cùng ngôn ngữ glass outline | ✅ Phase 0 + Phase 1 |
| Auth page cảm giác cùng "tone" với Landing (glass card + ink CTA) | ✅ Phase 2 |
| Bloom/session/tier có 1 nguồn duy nhất (token) | ✅ Phase 3 + Phase 4 |
| Insight / state surface đồng nhất | ✅ Phase 3 + Phase 4 |
| Admin chart palette + KPI card cùng ngôn ngữ | ✅ Phase 5 |
| Cyan giữ vai trò accent, không bị xóa | ✅ Đã document trong README + Phase 0 không động `bg-primary-600` |
| Hero gradient `from-indigo-600 via-cyan-500 to-teal-400` | ⚠️ **Chưa có phase nào tokenize gradient này** — README hứa "tokenize thành `.hero-gradient` class" nhưng không phase nào implement |

→ **Gap nhỏ:** thiếu task tokenize hero gradient. Có thể bổ sung vào Phase 0 (1 dòng `.hero-gradient` trong globals.css) hoặc Phase 3.

## Files Đã Đọc / Tham Chiếu

- `remaining tasks/sync-ui/README.md`
- `remaining tasks/sync-ui/phase-0-retint-buttons.md` → `phase-5-admin-chart-palette.md`
- `frontend/components/landing/LandingPage.tsx` (lines 98–110)
- `frontend/app/globals.css` (đã modified — đã có Phase 0)
- `frontend/tailwind.config.ts` (đã modified — đã có brand.ink + glass)
- `frontend/components/layout/PublicTopNav.tsx` (đã ink rồi)
- `frontend/app/(auth)/{login,register,forgot-password}/page.tsx` (còn 2 inline style mỗi file)
- `frontend/app/(protected)/{history,profile,dashboard}/page.tsx`
- `frontend/app/assessment/{page,results/page}.tsx`
- `frontend/app/quiz/[learningUnitId]/page.tsx`
- `frontend/app/module-test/[sectionId]/page.tsx`
- `frontend/package.json` (recharts 3.8.1)

## Khuyến Nghị Bước Kế Tiếp

1. **Lock 3 decision points** trong README (stat palette, tier mapping, avatar gradient).
2. **Re-scope Phase 1**: chuyển từ "5 file ad-hoc CTA" sang "Landing + PublicTopNav literal → class refactor" sau khi grep lại primary action buttons thật sự.
3. **Mark Phase 0 = verify-only** (token đã có, chỉ cần update test + visual sweep).
4. **Bổ sung `.hero-gradient` token** vào Phase 0 hoặc Phase 3.
5. Sau đó execute thứ tự: P0 verify → P1 (đã re-scope) → P2 → P3 (kèm stat token nếu chọn Option A) → P4 → P5.

## Verification End-to-End (Sau Khi Hoàn Thành)

```bash
cd frontend
npm run type-check
npm test -- --run frontend/tests/unit/{ui,landing,layout,auth,tokens,admin}
npm run build

# Grep guard
grep -rn -E '\bbg-(blue|emerald)-600\b' frontend/app/{assessment,quiz,module-test}/ frontend/components/{landing,layout}/
grep -rn 'style={{.*var(--' frontend/app/\(auth\)/

# Visual: Landing → /register → /login → /dashboard → /assessment → /quiz → /history → /profile → /admin/*
# Kỳ vọng: mọi primary CTA = ink rounded-full, mọi secondary = glass outline rounded-full
```
