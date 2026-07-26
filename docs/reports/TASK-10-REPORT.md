# TASK-10 report — 低擬真 Portal design system

## Outcome

完成。建立 plain CSS token foundation、mobile-first primitives、九個可存取 Astro components 與 fixture component gallery；未加入 framework plugin、Tailwind、theme 或品牌素材。

## Summary

CSS tokens 涵蓋色彩、spacing、typography、radii、borders、focus、touch target 與五類 semantic states。元件包含 navigation/footer、cards、buttons、forms、status/meta labels、alerts 及 loading/empty/error/success。案件狀態同時使用符號、中文文字、border/background，沒有只靠顏色傳達。

## Files changed

- `apps/portal/src/styles/tokens.css`：可換主題的低擬真 design tokens。
- `apps/portal/src/styles/global.css`：reset、focus、forms、buttons、skip link、mobile-first layout 與 reduced-motion。
- `apps/portal/src/components/{Card,StatusBadge,MetaLabel,Alert,StatePanel,FormField,ButtonLink,SiteHeader,SiteFooter}.astro`：核心 UI 元件。
- `apps/portal/src/components/ComponentGallery.astro`：fixtures copy 的靜態 gallery。
- `apps/portal/docs/DESIGN_SYSTEM.md`：tokens、components、keyboard/mobile/state/re-theme 規則與限制。
- `docs/reports/TASK-10-REPORT.md`：本報告。

## Commands executed

- `sed`：重讀 defaults、shared context、Task 09 report 與 Task 10 規格。
- `rg`：檢查 focus-visible、mobile media queries、ARIA roles、status symbol+label、tokens、所有必需 components/states。
- `npm run secrets`：檢查新增 CSS/Astro/docs。

## Verification

- Tests: 靜態 design-system checks 12/12 通過。
- Linters/type checks: Task 10 尚未安裝 Astro compiler；既有 `tsc` 只涵蓋 `.ts`。secret scan 通過。
- Builds: 明確延至 Task 11；目前不把未 compile 的 Astro components 誤報為 build 成功。
- Manual checks: native links/buttons/controls；3px visible focus；skip link；mobile single-column default；狀態都有 symbol+text；loading/error 使用 aria-live/aria-busy/alert；無 Tailwind/component library/custom art。

## Diagnostics

- `FormField` 能建立 label/hint/error IDs，但 Astro slot 無法自動替 child control 注入 `aria-describedby`；頁面作者必須明確連結，Task 13 測試補強。
- Color tokens 為中性 prototype 值，不代表 final branding；component CSS 沒有依賴品牌名稱。
- Base-path links 由 SiteHeader/SiteFooter props 注入，不在元件內寫死 root URL。

## Assumptions made

- System font 與 plain CSS 足以驗證第一版 IA，無需外部字型、Tailwind 或 component library。
- `ComponentGallery` 在 Task 11 由頁面 layout import global CSS 並掛到 `/components/`。
- 最小 touch target 採 2.75rem，後續 visual QA 可再加大但不可低於此 token。

## Risks and blockers

- 中度：元件尚未經 Astro build/runtime 驗證；Task 11 是必要前置驗收。
- 低度：尚未做瀏覽器 automated accessibility audit；Task 11–13 需加入 DOM tests 與 manual viewport/keyboard checklist。
- 無阻擋 Task 11 的問題。

## Questions for ChatGPT discussion

目前無需決定 final branding。品牌色、字型、logo 應在使用流程驗證後另開設計決策，不阻擋 Astro scaffold。

## Recommended next action

執行 Task 11：安裝 project-local Astro、建立 BaseLayout 與所有 Task 09 routes，把 gallery 掛上，並實際 static build/test configurable base path。

## Copy-paste handoff

> TASK-10 已完成：以 plain CSS 建立可 re-theme tokens（spacing/typography/radii/borders/focus/semantic states）、mobile-first shell/stack/cluster/grid、accessible forms/buttons/skip link，以及 9 個 Astro 元件與 fixture component gallery。五種案件狀態都有符號+繁中 label+border/background，不只靠顏色；loading/empty/error/success 有適當 ARIA。靜態設計系統檢查 12/12 通過，未引入 Tailwind、component library、品牌 template 或外部素材。Astro compiler 尚未安裝，因此 build 正確延至 TASK-11；下一步建立 static routes/BaseLayout 並實際 build。
