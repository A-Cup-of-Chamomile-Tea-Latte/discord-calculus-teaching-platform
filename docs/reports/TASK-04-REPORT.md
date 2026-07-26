# TASK-04 report — 本機工具鏈與品質基線

## Outcome

完成。Python、npm workspaces、format、lint、typecheck、tests、secret scan 與無部署 CI 均已建立；完整 `npm run check` 最終通過。

## Summary

以 npm scripts 提供單一命令介面。Python 使用標準 venv 與 project-local pytest/Ruff/mypy；Node 使用 npm workspaces 與 project-local TypeScript/Prettier。加入最小 typed smoke modules、三項 pytest、只回報位置與規則名稱的 secret scanner、四份空值 `.env.example`，以及 read-only、無 deploy job 的 CI。

## Files changed

- `pyproject.toml`：Python 3.12–3.14、setuptools、pytest、Ruff、mypy 與嚴格設定。
- `package.json`、`package-lock.json`：Node 24/npm 11 engine、兩個 workspaces、統一品質 scripts 與鎖定相依套件。
- `apps/portal/package.json`、`apps/portal/tsconfig.json`、`apps/portal/src/toolchain-smoke.ts`：Portal TypeScript workspace smoke baseline。
- `apps/gas/package.json`、`apps/gas/tsconfig.json`、`apps/gas/src/toolchain-smoke.ts`：GAS TypeScript workspace smoke baseline。
- `bots/__init__.py`、`bots/common/__init__.py`、`bots/common/toolchain_smoke.py`：可 typecheck 的 Python bot baseline。
- `tools/__init__.py`、`tools/quality/**`：只掃描 Git 可提交候選檔的輕量 secret scanner。
- `tests/test_toolchain_smoke.py`：fixture-only mode、scanner 拒絕假 token、repository 無 finding 三項測試。
- `.env.example`、`apps/portal/.env.example`、`apps/gas/.env.example`、`bots/.env.example`：只有變數名稱、沒有值。
- `.github/workflows/ci.yml`：Node 24/Python 3.12 上執行 `npm run check`，權限只有 `contents: read`，沒有部署。
- `docs/architecture/DEVELOPMENT.md`：標準 venv/npm、選用 uv、命令與安全邊界。
- `docs/reports/TASK-04-REPORT.md`：本報告。

## Commands executed

- `python3 -m venv .venv`：建立被 Git ignore 的本機 Python 環境。
- `.venv/bin/python -m pip install -e '.[dev]'`：只在 `.venv` 安裝 Python dev dependencies。
- `npm install`：安裝 workspace dev dependencies 並產生 lockfile；audit 結果 0 vulnerabilities。
- `npm run format`：修正一個 Ruff formatting 差異。
- `npm run check`：執行 secret scan、format check、lint、TS/Python typecheck 與 pytest。
- `npm ls --depth=0`、`pytest --collect-only`、`git check-ignore`：版本、測試數與 ignore 驗證。

## Verification

- Tests: pytest 3/3 passed，0 failed（0.03s）。
- Linters/type checks: Ruff lint 全通過；Ruff format 7 files already formatted；Prettier 全部 matched；TypeScript 兩個 workspaces 皆通過；mypy 7 source files、0 issues。
- Builds: Task 04 不安裝產品框架，無產品 build；editable Python package build/install 成功。
- Secret scan: 101 個 Git 可提交候選檔，0 findings；scanner 拒絕假 assigned-token 的測試通過。
- Dependency checks: npm 安裝 4 packages、audit 0 vulnerabilities；實際為 TypeScript 5.9.3、Prettier 3.9.5。Python 實際為 pytest 9.1.1、Ruff 0.15.22、mypy 1.20.2。
- Manual checks: `.venv`、`node_modules`、`.env` 均被 ignore；`.env.example` 未被 ignore；Git remote 仍為 0。

## Diagnostics

- Python 3.14.6 可成功安裝並執行目前品質套件，Task 02 的相容性疑慮對 foundation tooling 已解除；discord.py 仍須 Task 21 實測。
- Node 24/npm 11 workspaces 正常，TypeScript 5.9.3 與 Prettier 3.9.5 通過。
- 首次非提權 check 因 sandbox 不允許在指定外部路徑建立 `.ruff_cache` 而停止；允許寫入後發現一個真實格式差異。執行 formatter 後完整 check 通過。這不是 repository 或工具相容性問題。
- CI 不含 secrets、deployment、Pages 或雲端 service action。

## Assumptions made

- Node 24.x/npm 11.x 依 Task 02 的實際環境作本階段 engine 基線；Task 11 安裝 Astro 時若 upstream 有更窄要求，再以實測更新。
- CI 用 Python 3.12 作保守最低支援版本；本機另以 3.14.6 驗證。
- Task 04 只安裝工具鏈，不提前安裝 Astro、discord.py 或 clasp。
- `.env.example` 中 deployment/script ID 只代表未來設定名稱，空值不構成部署設定或 secret。

## Risks and blockers

- 低度：目前沒有 Python lockfile；版本由範圍限制，Node 已有 lockfile。Task 30 可決定是否加入 uv/pip lock，且標準 pip 路徑必須繼續受支援。
- 低度：輕量 scanner 只攔截常見明顯 pattern，不取代 GitHub secret scanning 或專業工具；目前不建立 remote，Task 29/30 再加深。
- 無阻擋 Task 05 的問題。

## Questions for ChatGPT discussion

目前沒有需在文件任務前決定的工具鏈問題。是否採 Python lockfile 可延至 Task 30。

## Recommended next action

執行 Task 05：以繁體中文完成 project charter、glossary 與不誇大技術的 proposal preface draft。

## Copy-paste handoff

> TASK-04 已完成：建立 npm workspaces 與 Python venv 的 project-local 工具鏈，單一 `npm run check` 會執行 secret scan、Prettier/Ruff format、Ruff lint、兩個 TypeScript workspace typecheck、mypy 與 pytest。最終結果為 pytest 3/3 passed、mypy 7 files 0 issues、TS 兩 workspace 通過、secret scan 101 files 0 findings、npm audit 0 vulnerabilities。加入四份只有名稱無值的 `.env.example`、本機設定文件與只讀無部署 CI。Python 3.14 foundation tooling 相容性已實測正常；discord.py 後續再驗證。沒有 remote、部署、外部服務或 secrets。下一步執行 TASK-05 charter、glossary、proposal preface。
