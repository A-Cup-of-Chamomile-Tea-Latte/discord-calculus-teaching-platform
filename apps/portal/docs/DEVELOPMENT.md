# Portal development

## Runtime

- Astro 7 static output、strict TypeScript、原生瀏覽器 API。
- 沒有 React/Vue/Svelte、SSR adapter 或 production API client。
- `FixtureCaseLookupAdapter` 直接 import monorepo 的虛構 JSON，build 不需 backend/network。

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm install
```

## Commands

| Command                                                      | Result                                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| `npm run dev --workspace @calculus/portal`                   | Local Astro dev server；不連正式服務                                      |
| `npm run check --workspace @calculus/portal`                 | Astro diagnostics + strict TS                                             |
| `npm run test --workspace @calculus/portal`                  | Vitest adapter/path unit tests                                            |
| `npm run build --workspace @calculus/portal`                 | Static output to `apps/portal/dist`                                       |
| `npm run preview --workspace @calculus/portal`               | Local preview of the last build                                           |
| `npm run verify:dist --workspace @calculus/portal -- /base/` | Required-route、zh-Hant、identifier leak 與 base-safe link verification   |
| `npm run verify:pages --workspace @calculus/portal`          | Pages workflow manual gate、permissions、secret 與 artifact dry-run check |

Root `npm run check` 會執行 Portal tests/typecheck 與 Python tests；root `npm run build` 會 build 所有有 build script 的 workspaces。

## Routes

- `/`, `/cases/`, five fixture `/cases/[caseNumber]/` pages
- `/join/`, `/ask/`, `/private-support/`, `/guide/`, `/status/`
- local gallery `/components/` and `/404.html`

## Base path

`astro.config.mjs` 將 `ASTRO_BASE_PATH` 正規化為 root 或 project path。所有 internal links 經 `withBase()`；完整 GitHub Pages workflow 與 deployment manual actions 見 `GITHUB_PAGES.md`。

```sh
ASTRO_BASE_PATH=/discord-calculus-teaching-platform npm run build --workspace @calculus/portal
npm run verify:dist --workspace @calculus/portal -- /discord-calculus-teaching-platform/
```

`ASTRO_SITE_URL` 是可選的 public origin build variable；未設定時不猜測 owner 或 production URL。完整 Pages manual actions、least-permission workflow 與 custom-domain migration note 見 `GITHUB_PAGES.md`。

## Fixture adapter boundary

`CaseLookupAdapter` 只輸出 `PublicCaseView`，不傳 internal case/user/message ID、Discord snowflake、hash 或 Private Support。正式 GAS adapter 必須實作相同 lookup/list interface，並在 server side 完成 type/visibility policy；瀏覽器不可取得 credential。

## Preview checklist

1. 以鍵盤從 skip link 走過 header、case search、actions 與 footer。
2. 在 320px、375px、768px、desktop 檢查無水平 overflow。
3. 確認 status badge 有符號與文字，error/fallback 有下一步。
4. 在 `/portal-test/` preview 點遍 header/footer/case links，不得跳回 domain root。
5. View source 搜尋 Discord snowflake、Private Support ID、token/secret，結果應為 0。
