# Portal development（post-v13 candidate）

## Runtime boundary

- Astro 7 static output、strict TypeScript、原生瀏覽器 API。
- reviewer build 可使用虛構 fixtures 展示內部頁；public artifact 不含 fixture 成功結果。
- `SameOriginJoinAdapter` 與 `SameOriginCaseLookupAdapter` 只呼叫受設定允許的 same-origin endpoint。
- backend 實作位於 `runtime/discord-course-bots`；Portal 本身不持有 session authority、SQLite 或 Discord credential。

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm install
```

## Commands

| Command                                                        | Result                                                        |
| -------------------------------------------------------------- | ------------------------------------------------------------- |
| `npm run dev --workspace @calculus/portal`                     | Local Astro dev server；不連 production                       |
| `npm run check --workspace @calculus/portal`                   | Astro diagnostics + strict TypeScript                         |
| `npm run test --workspace @calculus/portal`                    | Vitest adapters、contracts、paths 與 public boundary tests    |
| `npm run build --workspace @calculus/portal`                   | 產生 reviewer static artifact                                 |
| `npm run build:public --workspace @calculus/portal`            | 產生並裁切 public 五頁 artifact                               |
| `npm run verify:public --workspace @calculus/portal -- /base/` | 驗證 allowlist pages、fail-closed、敏感字串與 base-safe links |
| `npm run verify:pages --workspace @calculus/portal`            | 驗證 Pages workflow 的手動 deploy gate 與最小權限             |

## Routes

Public allowlist：

- `/`、`/join/`、`/cases/`、`/guide/`、`404.html`

Reviewer only：

- `/access/`、`/components/`、`/scenarios/`、`/settings/`、`/sqlite-lab/`、`/status/`、`/team/`、`/team/registrations/`
- 舊 `/ask/`、`/private-support/`、`/discord-guide/` 只保留封存提示，public build 移除。

## Public dynamic capability

課程 Discord 邀請由 `PUBLIC_DISCORD_INVITE_URL` 注入，只接受 Discord 官方 HTTPS 邀請網址。未設定時，加入頁保留官方 APP 下載與網頁版入口，但不顯示可點擊的假課程邀請。

本機 artifact 可用下列同源 path 驗證表單 wiring：

```sh
ASTRO_BASE_PATH=/~calc/DC-platform-beta \
ASTRO_SITE_URL=https://www.math.ntu.edu.tw \
PUBLIC_JOIN_APPLICATION_ENDPOINT=/~calc/DC-platform-beta/api/join \
PUBLIC_CASE_STATUS_ENDPOINT=/~calc/DC-platform-beta/api/cases/lookup \
PUBLIC_PORTAL_SESSION_ENDPOINT=/~calc/DC-platform-beta/api/session \
npm run build:public --workspace @calculus/portal

npm run verify:public --workspace @calculus/portal -- /~calc/DC-platform-beta
```

沒有 endpoint 時，加入與查詢都必須顯示服務尚未啟用；這是安全預設，不是故障。deployment 前仍須注入正式 signed session、CSRF、origin allowlist、rate limit、durable audit sink 與 TLS cookie，並完成白帳號 E2E。

## Preview checklist

1. 以鍵盤從 skip link 走過 header、加入、案件查詢、指南與 footer。
2. 在 320px、375px、768px、desktop 檢查無水平 overflow。
3. 確認 public artifact 恰為五頁，且找不到 reviewer／封存 routes。
4. 未設定 backend 時，首頁、加入與案件查詢不得顯示成功 fixture。
5. 已設定本機 path 時，確認 request 仍為 same-origin，Browser 中沒有 token、DB path 或 credential。
6. View source 搜尋 Discord snowflake、Private 內容、Email、token／secret 與 fixture internal ID，結果應為 0。
