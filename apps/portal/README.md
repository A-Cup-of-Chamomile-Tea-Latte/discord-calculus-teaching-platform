# Portal

Astro + TypeScript 靜態入口網站，負責 onboarding、隱私說明、網站代送問題與按需案件查詢。內建「課程正式／學生友善」兩套 token-based 外觀，以及標示人工驗證日期的系統狀態頁。它不持有 Discord token、不直接存取正式 Sheets，也不取代 NTU COOL。

## Local commands

在 monorepo root 完成 `.venv` 與 `npm install` 後：

```sh
npm run dev --workspace @calculus/portal
npm run check --workspace @calculus/portal
npm run test --workspace @calculus/portal
npm run build --workspace @calculus/portal
npm run preview --workspace @calculus/portal
```

Project-site base-path dry run：

```sh
ASTRO_BASE_PATH=/portal-test npm run build --workspace @calculus/portal
npm run verify:dist --workspace @calculus/portal -- /portal-test/
npm run verify:pages --workspace @calculus/portal
```

所有 routes 使用 repository fixtures；dev/build/test 不需要 API URL、OAuth secret、Discord token 或 Google credential。詳細開發說明見 `docs/DEVELOPMENT.md`；Pages 部署前人工步驟與 custom-domain note 見 `docs/GITHUB_PAGES.md`。
