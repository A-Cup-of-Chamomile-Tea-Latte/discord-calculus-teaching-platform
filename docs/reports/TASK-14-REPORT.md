# TASK-14 report — GitHub Pages project-site preparation

## Outcome

Complete。GitHub Pages project-site workflow、artifact upload、environment-driven Astro site/base、部署前人工步驟與 custom-domain migration note 均已準備並完成本機 dry run；沒有建立 remote、push、啟用 Pages、dispatch 或部署。

## Summary

- 新增 Pages workflow：main 相關變更只 build/test/verify/upload artifact；真正 deploy 必須手動 dispatch 並明確設 `deploy=true`。
- Build job 只有 `contents: read`；deploy job 只有 `pages: write` 與 `id-token: write`，使用 `github-pages` environment。
- Workflow 以 GitHub context 設定 `ASTRO_BASE_PATH=/<repository>` 與 `ASTRO_SITE_URL=https://<owner>.github.io`，不硬編碼 token 或 secret。
- 使用官方 Pages actions 的 2026 current major：`upload-pages-artifact@v5` 與 `deploy-pages@v5`。
- 加入 local workflow verifier，檢查 trigger、manual gate、permissions、no secrets、base/site variables、artifact path 與 action majors。
- 建立完整 deployment manual actions、既有 owner site 保護聲明、expected URL pattern、rollback awareness 與 custom-domain migration note。
- 用建議 repository `discord-calculus-teaching-platform` 與目前 owner 假設完成非 root base production build/dry run。

## Files changed

- `.github/workflows/pages.yml`：build/upload + manually gated deploy workflow。
- `.github/workflows/README.md`：區分 CI 與 Pages workflow 的執行範圍。
- `apps/portal/scripts/verify-pages-workflow.mjs`：least-permission/no-secret/manual-gate 靜態驗證。
- `apps/portal/package.json`：新增 `verify:pages` script。
- `apps/portal/docs/GITHUB_PAGES.md`：預期 URL、dry run、所有外部人工步驟、custom-domain 與 rollback note。
- `apps/portal/docs/DEVELOPMENT.md`：補 Pages verifier 與部署文件入口。
- `apps/portal/README.md`：補 workflow dry-run command 與文件連結。
- `docs/reports/TASK-14-REPORT.md`：本任務交接報告。

`astro.config.mjs` 已在 Task 11 實作 safe `ASTRO_BASE_PATH` normalization 與 optional `ASTRO_SITE_URL`；Task 14 直接驗證並由 workflow 提供這兩個 build variables，無需重寫。

## Commands executed

- GitHub 官方 Pages、upload-pages-artifact、deploy-pages 與 custom-domain 文件 read-only 查核。
- `npx prettier --write <Task 14 workflow/scripts/docs>`
- `npm run verify:pages --workspace @calculus/portal`
- `ASTRO_BASE_PATH=/discord-calculus-teaching-platform ASTRO_SITE_URL=https://A-Cup-of-Chamomile-Tea-Latte.github.io npm run build --workspace @calculus/portal`
- `npm run verify:dist --workspace @calculus/portal -- /discord-calculus-teaching-platform/`
- `rg` 掃描 dist root-relative href/src。
- `git status --short -- .github apps/portal docs/reports`（read-only）。

沒有執行 `git remote` mutation、remote repository creation、push、Pages settings change、workflow dispatch、DNS change 或 deployment。

## Verification

- Tests：Portal Vitest 4 files、17 tests passed（Task 13 最新基線）。
- Linters/type checks：完整 root check 通過；secret scan 226 files / 0 findings；Prettier、Ruff lint/format、GAS TypeScript、mypy（9 source files）均通過；Astro check 39 files，0 errors、0 warnings、0 hints；Task 14 workflow verifier passed。
- Builds：建議 owner/repository variables 的 static build 成功，14 pages；dist verifier 通過 10 required pages、131 base-safe links。
- Manual checks：額外 regex 掃描沒有 root-relative href/src 逃離 `/discord-calculus-teaching-platform/`；workflow 沒有 `${{ secrets.* }}` reference；owner-site 路徑不在 repository/worktree 中且未觸碰。

## Diagnostics

- GitHub 官方 current flow 仍是 checkout/build → upload Pages artifact → deploy Pages artifact；deploy job 需要 `pages: write`、`id-token: write` 並建議 `github-pages` environment。
- 2026-07 查核顯示 `actions/upload-pages-artifact@v5` 與 `actions/deploy-pages@v5` 已發布；兩者的 v5 轉用／依賴 Node 24 generation，與 repository Node 24 baseline 一致。
- Workflow 的 push trigger會建立可部署 artifact，但不會部署；這能先觀察 remote CI，再由維護者手動授權 external state change。
- GitHub Pages 是公開 hosting；即使 source repository visibility 不等於 public，也不能假設 Pages 內容私密。

## Assumptions made

- Owner 暫記為 `A-Cup-of-Chamomile-Tea-Latte`，repository 暫記為 `discord-calculus-teaching-platform`；兩者都必須在 external action 前再次確認。
- Default branch 預設為 `main`；若 remote 不同需改 workflow trigger 與 environment protection。
- 在預設 GitHub project-site URL 使用 `/<repository>/` base；dedicated custom domain 才切回 `/`。
- Workflow major tags接受 GitHub 維護的相容更新；若組織政策要求 immutable SHA，Task 30 應 pin 並建立更新流程。

## Risks and blockers

- 高度：任何 deployment 都會把 fixture portal 公開到 internet；必須先完成 Task 29 security/privacy 與 Task 33 go/no-go。
- 高度：owner/repository 尚未由 external GitHub state 驗證；不可據此建立 remote 或修改既有 owner site。
- 中度：major-tag Actions 可能變動；若 supply-chain policy 要求 SHA pinning，需在正式 deploy 前處理。
- 中度：custom domain 若先設 DNS、未先在 GitHub 驗證/設定，可能產生 takeover 風險；migration note 已明列順序與禁止 wildcard。
- 外部阻擋只影響真正 deployment，不影響 Task 14 local preparation。

## Questions for ChatGPT discussion

- 最終 owner、repository name、visibility 與 default branch 是否確定？
- 是否要求 GitHub Actions 全部 pin immutable SHA，而非 official major tag？
- `github-pages` environment 是否需要 required reviewer，以及 reviewer 是誰？
- Portal 何時通過 privacy review，可以公開；需要哪些 unpublish/incident owner？

## Recommended next action

執行 Batch C（Tasks 15–19）：建立完全本機的 GAS/clasp scaffold、Sheets schema、case API、activation nonce 與 email verification skeleton；保持 mock adapters，不建立 Apps Script project、不 deploy、不寄信。

## Copy-paste handoff

Task 14 已完成 GitHub Pages project-site 的本機準備：新增 `.github/workflows/pages.yml`，push 只 build/test/verify/upload artifact，真正 deploy 只有手動 dispatch 且 `deploy=true`；build job 僅 `contents: read`，deploy job僅 `pages: write`/`id-token: write`，無 secrets。Workflow 用 repository/owner context 設定 Astro base/site，使用 2026 current `upload-pages-artifact@v5`、`deploy-pages@v5`。以 `A-Cup-of-Chamomile-Tea-Latte` / `discord-calculus-teaching-platform` 假設 dry run 成功：14 pages，10 required pages、131 links 全部 base-safe，workflow verifier 通過。已寫完整人工步驟、既有 owner site 保護、custom-domain/rollback note。沒有建立 remote、push、啟用 Pages、dispatch、DNS 或部署。正式外部動作前需確認 owner/repo/visibility/default branch、Action SHA policy、environment reviewer，並先完成 privacy/go-no-go。建議下一步 Batch C Tasks 15–19。
