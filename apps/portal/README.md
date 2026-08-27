# Portal

Astro 7 + TypeScript 的靜態入口網站。學生面只負責加入申請入口、使用／隱私指南與一次一案的最小狀態查詢；提問內容與附件一律留在 Discord，Private Support 由 `/private open` 建立。

公開 artifact 固定為 `/`、`/join/`、`/cases/`、`/guide/` 與 `404` 五頁。Course Manager、設定、狀態、SQLite lab 與封存頁只存在 reviewer build；舊 `/ask/`、`/private-support/`、`/discord-guide/` 不進 public artifact。

加入頁以 Discord APP 為主要建議，同時保留官方網頁版備援。正式課程邀請由 `PUBLIC_DISCORD_INVITE_URL` 注入；只接受 `https://discord.gg/...` 或 `https://discord.com/invite/...`，未設定或格式錯誤時一律不產生邀請按鈕。

v13 Portal candidate 已有加入介面、Email 驗證、durable SQLite outbox、provider adapter 與案件查詢，並以暫存 SQLite／capturing adapter 完成本機 journey。quota-aware 申請意向排程、正式 session issuer、真實寄送驗收與外部部署仍未完成。未設定受核准 endpoint 時，public build 必須 fail closed，不得用測試資料冒充成功。Browser 不持有 Discord token、Google owner credential、SQLite path 或 writer access。

## Local commands

在 monorepo root 完成 `npm install` 後：

```sh
npm run dev --workspace @calculus/portal
npm run check --workspace @calculus/portal
npm run test --workspace @calculus/portal
npm run build --workspace @calculus/portal
npm run preview --workspace @calculus/portal
```

Public artifact dry run：

```sh
ASTRO_BASE_PATH=/~calc/DC-platform-beta \
ASTRO_SITE_URL=https://www.math.ntu.edu.tw \
PUBLIC_JOIN_APPLICATION_ENDPOINT=/~calc/DC-platform-beta/api/join \
PUBLIC_CASE_STATUS_ENDPOINT=/~calc/DC-platform-beta/api/cases/lookup \
PUBLIC_PORTAL_SESSION_ENDPOINT=/~calc/DC-platform-beta/api/join \
npm run build:public --workspace @calculus/portal

npm run verify:public --workspace @calculus/portal -- /~calc/DC-platform-beta
```

上述 endpoint 只用於本機 artifact 驗證，不代表 backend 已公開部署。若省略 endpoint，學生面會顯示服務尚未啟用。

詳細開發說明見 `docs/DEVELOPMENT.md`；same-origin 安全邊界見 `../../docs/ops/PORTAL_BACKEND_V1.md`；Beta 分工與 Google 配額見 `../../docs/ops/DC_PLATFORM_BETA_LAUNCH_CHECKLIST.md`；外部發布仍須人工 gate，見 `docs/GITHUB_PAGES.md`。
