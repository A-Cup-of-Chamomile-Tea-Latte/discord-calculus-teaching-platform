# TASK-30 report — unified tests, builds, and non-deploying CI

## Outcome

Complete。已建立 fresh-checkout、無 secrets、無部署的六路 CI quality gate，涵蓋 contracts、fixtures、Portal、GAS、Python、secret/no-real-data guards、GitHub Pages base path，以及 generated export/anonymization/import validation。

## Summary

- `.github/workflows/ci.yml` 拆成 `code-quality`、`contracts-and-fixtures`、`python-tests`、`generated-exports`、`portal`、`gas` 六個 jobs；每個失敗可獨立定位。`python-tests` 另跑 root pytest，確保新 test directory 不會因未加入分流而漏接。
- Node jobs 使用 Node 24 + `npm ci` + npm cache；Python jobs 使用 Python 3.12 + editable dev install + pip cache。Workflow 全域只有 `contents: read`，沒有 secret reference、write permission、environment、deploy action 或雲端應用命令。
- 新增 repository quality tests：所有 fixture/contract example 必須 UTF-8、JSON 可解析、email 只能是 `example.com`，並拒絕 NTU domain、臺灣電話格式與明顯 credential/private-key shapes；另以 test 固定 CI job、cache 與 non-deploying invariants。
- Portal dist verifier 從只檢查 10 個 required pages 的 `href`，加強為掃描全部 14 個 generated HTML 的 `href`/`src`/`action`，驗證 project-site base prefix、local target 存在且不能 path traversal。
- `.github/workflows/README.md` 列出每個 CI job 的本機等價命令與部署隔離邊界。
- Task 14 的 `pages.yml` 保持獨立且未被執行；Task 30 CI 不上傳、不發布、不部署。

## Files changed

- `.github/workflows/ci.yml`：六個有 cache 的 non-deploying quality jobs。
- `.github/workflows/README.md`：CI gate、本機等價命令與 Pages workflow 邊界。
- `tests/quality/__init__.py`：repository-level quality test package。
- `tests/quality/test_repository_quality_gates.py`：fixture no-real-data、JSON/UTF-8、CI policy/cache tests。
- `apps/portal/scripts/verify-dist.mjs`：全 generated pages 的 base-safe/broken-link/path-escape validation。
- `docs/reports/TASK-30-REPORT.md`：本報告。

沒有修改 Task 28/29/31/32/33 的 implementation 或報告檔案。

## Commands executed

- 閱讀 `PROJECT_DEFAULTS.md`、Tasks 00/01/30、task report template、相關 Tasks 04/07/08/14/19/25/25A/26/27 reports、workflows、workspace manifests、既有 tests/build verifiers。
- `npx prettier --write ...`、`.venv/bin/python -m ruff format tests/quality`、`.venv/bin/python -m ruff check tests/quality`。
- `.venv/bin/python -m pytest -q tests/contract tests/quality`。
- `.venv/bin/python -m pytest -q`。
- `.venv/bin/python -m pytest -q tests/tools`。
- Portal workspace 的 `check`、`test`、project-base `build`、`verify:dist`。
- GAS workspace 的 `typecheck`、`test`、`build`。
- `npm run check`、`git diff --check`。

沒有 push、commit、workflow dispatch、Pages upload/deploy、clasp、Discord/GAS/Sheets/email/OAuth/network application call、真實 credential 或真實資料。

## Verification

- Full local gate：`npm run check` passed。
- Python full suite：113/113 passed（含 Task 32 fixture-only end-to-end journey 1/1）；另有既有 discord.py 2.7.1 / Python 3.14 的 2 個 deprecation warnings，0 failures。
- CI diagnostic split counts：contracts + fixtures + quality 40/40；generated export/anonymizer/importer 18/18。`python-tests` 再跑完整 113/113，避免新增 test directory 漏接。
- Portal：Vitest 25/25；Astro 41 files、0 errors / 0 warnings / 0 hints；14 static pages built；184 個 `href`/`src`/`action` references 全部 base-safe 且 local targets 存在。
- GAS：Vitest 44/44；TypeScript no-emit typecheck passed；`dist/Code.js` + `dist/appsscript.json` local bundle passed。
- Static quality：Prettier passed；Ruff format 68 files、lint passed；strict mypy 68 source files、0 issues；secret scan 361 candidates / 0 findings。
- Fixture guard：43 個 root fixtures、GAS fixtures、contract example files 可讀；所有 JSON 可解析；0 forbidden domains/phones/secret shapes/non-example email domains。
- CI invariant tests：4/4 passed；六個 required jobs、npm/pip caches、read-only/no-secret/no-deploy constraints 全部成立。
- GitHub Actions 未在 remote runner 執行，因本任務禁止 push/remote action；本機 Node 24.13/npm 11.6.2 與 Python 3.14.6 的等價命令已全綠。CI 明確固定 project-supported Python 3.12，fresh runner 會由 setup action 安裝。

## Diagnostics

- 原 CI 只有單一 `quality` job，Portal 只額外 build；任何 contracts、GAS、export 或 no-real-data failure 都難以定位。六路切分解除這個診斷盲點，但會重複安裝 dependencies；setup-node/setup-python cache 降低成本。
- 原 Portal verifier 只掃 required pages 的 `href`，漏掉額外 dynamic case pages、scripts、forms 與 broken local targets；目前掃描全部 generated HTML 與三種 URL-bearing attributes。
- `pages.yml` 仍含 Task 14 的手動 deploy path。它不由 Task 30 CI 呼叫，但正式 repository 啟用前仍需由 owner review branch protection、environment approval 與 visibility policy。
- Python 3.14 warnings 來自 discord.py dependency 的 `asyncio.iscoroutinefunction`，不是本任務 regression；CI 用 Python 3.12 不會掩蓋 application failure。

## Assumptions made

- CI 使用最低支援 Python 3.12，與 `pyproject.toml` 一致；本機因沒有 Python 3.12 executable，以 3.14.6 驗證等價命令。
- `example.github.io` 與 `/discord-calculus-teaching-platform` 只作 deterministic static-build fixture，不表示 owner/repository/Pages 已建立或公開。
- CI dependency registry download 是 fresh-runner 安裝必要條件；「無外部服務呼叫」解釋為 application 不連 Discord、Google、email、OAuth 或 production API。
- Generated export gate 以 pytest temporary directories 產生 fixture packages，不讀寫 Git-ignored production-like export directories。

## Risks and blockers

- 低：六個 jobs 重複 installation，cold cache 時較慢。Mitigation：已有 lockfile/manifest-based caches；保持 job isolation 以換取可診斷性。
- 低：pattern-based real-data/secret guards 不能數學證明文本虛構。Mitigation：fixtures 仍需 review，且 analysis release 應遵循 Task 27/29 human review gate。
- 低：workflow syntax 尚未由 GitHub hosted runner 實際執行。Mitigation：未來建立 remote 後先開 pull request 驗證，不給 write permission、不加入 secrets、不與 deploy workflow合併。
- 無阻擋後續文件、integration plan 或 final diagnostic 的問題。

## Questions for ChatGPT discussion

- 正式 remote 建立後，是否要求六個 jobs 全部成為 branch-protection required checks？
- `pages.yml` 的手動 deploy 是否應在 repository visibility/access-scope 決策完成前完全停用，而不只保留 manual boolean gate？

## Recommended next action

執行 Task 31 documentation/demo/preface，讓使用者與 reviewer 有一條完全 fixture-only、可重現且不會誤觸部署的操作路徑；之後以 Task 32 integration plan 與 Task 33 final diagnostic 收斂。

## Copy-paste handoff

Task 30 已完成 unified non-deploying CI：六個獨立 jobs 分別檢查 formatter/lint/types/secrets、contracts+fixtures+no-real-data、完整 Python suite、generated export/anonymizer/importer、Portal、GAS。Fresh checkout 使用 Node 24 `npm ci` 與 Python 3.12 editable dev install，npm/pip cache；workflow 只有 `contents: read`，沒有 secrets、write permission、environment、deploy action、clasp 或 application external calls。新增 4 個 repository quality tests，掃 43 個 fixture/example files，禁止 NTU domain、臺灣電話、明顯 secrets 與非 example.com emails。Portal verifier 現在掃全部 14 generated pages、184 個 href/src/action，驗證 project-site base、target existence 與 path escape。完整結果：Python 113/113（含 Task32 fixture journey 1/1）、Portal 25/25、GAS 44/44、mypy 68 files 0 issues、Astro 41 files 0 diagnostics、secret scan 361/0；只有既有 discord.py/Python 3.14 的 2 warnings。Portal 14 pages與GAS bundle成功。Task 30 沒有 dispatch/push/upload/deploy；Task14 pages workflow仍獨立。建議下一步完成 Task31 docs/demo，之後 Task33 final diagnostic。
