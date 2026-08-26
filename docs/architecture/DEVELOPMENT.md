# 本機開發指南

## 必要條件

- Node.js 24.x、npm 11.x。
- Python 3.12–3.14；CI 以 Python 3.12 作最低驗證版本。
- Git。

不需要全域安裝 Astro、TypeScript、Ruff、pytest、mypy、discord.py 或 clasp。下列步驟只建立本機開發環境，不登入外部服務。

## 全新安裝

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm install
npm run check
npm run build
```

Root npm scripts use `tools/run-python.mjs`: they prefer `PYTHON`, an active
virtual environment, then the repository `.venv`. Git worktrees also resolve
the main checkout's shared `.venv`, so `npm run check` does not depend on a
global `python` shim or repeated manual `PATH` overrides.

在 CI 或需要嚴格依 `package-lock.json` 安裝時，使用 `npm ci` 取代 `npm install`。Windows PowerShell 啟用指令為 `.venv\\Scripts\\Activate.ps1`。

## 本機 Portal

```sh
npm run dev --workspace @calculus/portal
```

開啟 Astro 顯示的 localhost URL。開發 server 只服務本機 fixture portal；不需要 API URL、OAuth secret、Discord token 或 Google credential。結束時在終端按 `Ctrl-C`。

Static build / preview：

```sh
npm run build --workspace @calculus/portal
npm run preview --workspace @calculus/portal
```

## 統一品質界面

| 指令                   | 用途                                                                      |
| ---------------------- | ------------------------------------------------------------------------- |
| `npm run secrets`      | 掃描可提交候選檔的明顯 secret pattern，不印出值                           |
| `npm run format`       | 格式化 app 與 Python 程式碼；Markdown 可用 `npx prettier --write <files>` |
| `npm run format:check` | Prettier + Ruff format check                                              |
| `npm run lint`         | Ruff lint                                                                 |
| `npm run typecheck`    | Astro/GAS TypeScript 與 Python mypy                                       |
| `npm run test:js`      | Portal 與 GAS unit tests                                                  |
| `npm run test:py`      | contracts、fixtures、bots 與 local tools pytest                           |
| `npm run check`        | secrets → format check → lint → typecheck → all tests                     |
| `npm run build`        | Portal static artifact 與 GAS local bundle                                |

## 單一 lane 指令

```sh
npm run check --workspace @calculus/portal
npm run test --workspace @calculus/portal
npm run build --workspace @calculus/portal

npm run typecheck --workspace @calculus/gas
npm run test --workspace @calculus/gas
npm run build --workspace @calculus/gas

python -m pytest tests/tools/test_discord_export.py
python -m pytest tests/tools/test_anonymizer.py
python -m pytest tests/tools/test_sheets_importer.py
```

## GitHub Pages base-path dry run

Project site 不在 domain root，因此 routes 與 assets 必須對 `/<repository>/` 安全：

```sh
ASTRO_BASE_PATH=/discord-calculus-teaching-platform \
ASTRO_SITE_URL=https://example.invalid \
npm run build --workspace @calculus/portal

npm run verify:dist --workspace @calculus/portal -- \
  /discord-calculus-teaching-platform/
npm run verify:pages --workspace @calculus/portal
```

`example.invalid` 是不可解析的文件範例，不是部署目的地。上述命令只在本機建立與檢查 artifact，不 push 也不 deploy。

## 環境檔與 local data

日常 fixture demo 不需要任何 secret。各 component 的有效變數、實際讀取者與已淘汰名稱見[設定總覽](../CONFIGURATION.md)。個人 `.env`、`.clasp.json`、tokens、credentials、deployment IDs、`exports/` 與 `local-data/` 都不得提交。

## 預覽檢查

1. 從 skip link 開始，用鍵盤走過 header、case search、forms 與 footer。
2. 在 320 px、375 px、768 px 與 desktop 檢查無水平 overflow。
3. 用 `C01-7K4M2Q-0702-1000`、不存在的 well-formed 編號與 malformed 輸入檢查 found/not-found/error 文案。
4. 確認表單標示 fixture mode 且只產生本頁 confirmation。
5. 確認 Private Support 不在 public case list/search。
6. 確認 status/fallback 文案提供明確下一步，且不把「未連接」說成正式服務中斷。

完整示範見 [Fixture demo](../FIXTURE_DEMO.md)；部署前手動關卡見 [尚未部署](../DEPLOYMENT_NOT_DONE.md)。
