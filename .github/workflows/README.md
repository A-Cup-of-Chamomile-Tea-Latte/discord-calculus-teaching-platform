# Workflows

## `ci.yml`：non-deploying quality gates

CI 只讀 checkout，在 fresh checkout 使用 `npm ci` 與 `pip install -e ".[dev]"`，不需要 repository secret、真實資料或外部服務帳號。六個獨立 jobs 讓失敗來源清楚可見：

| Job                      | Local equivalent                                                                                                                                                                          | Gate                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `code-quality`           | `npm run secrets && npm run format:check && npm run lint && npm run typecheck`                                                                                                            | secret patterns、formatter、Ruff、TypeScript、mypy                          |
| `contracts-and-fixtures` | `.venv/bin/python -m pytest -q tests/contract tests/quality`                                                                                                                              | JSON contracts、fixtures、no-real-data guard、CI policy                     |
| `python-tests`           | `.venv/bin/python -m pytest -q`                                                                                                                                                           | 完整 Python suite；也防止新增 test directory 未被分流漏接                   |
| `generated-exports`      | `.venv/bin/python -m pytest -q tests/tools`                                                                                                                                               | raw export、sanitization、batch importer generated outputs                  |
| `portal`                 | `ASTRO_BASE_PATH=/discord-calculus-teaching-platform ASTRO_SITE_URL=https://example.github.io npm run build --workspace @calculus/portal`，再執行 workspace 的 check、test、`verify:dist` | Portal logic、Astro diagnostics、static build、GitHub Pages base-safe links |
| `gas`                    | `npm run typecheck --workspace @calculus/gas && npm run test --workspace @calculus/gas && npm run build --workspace @calculus/gas`                                                        | GAS pure logic、types、local bundle                                         |

`ci.yml` 沒有 deploy job、environment、write permission、secret reference 或雲端 API 呼叫。Dependency cache 只使用 lockfile／`pyproject.toml` 作 key；cache miss 時仍能從標準安裝命令重建。

## `pages.yml`：Task 14 的獨立未來部署準備

`pages.yml` 不屬於 Task 30 CI。Push path 只會 build、test、verify 與上傳 Pages artifact；真正 deploy job 必須由維護者手動 dispatch 並把 `deploy` 設為 `true`。Task 30 沒有 dispatch、push、啟用 Pages 或部署。操作與 rollback 見 `apps/portal/docs/GITHUB_PAGES.md`。
