# GitHub Pages project-site deployment（保留方案）

此文件保留 GitHub Pages 的備援做法，不是目前的部署授權。Portal 尚未進入 external staging，數學系網站掛載也未獲授權；不得依本文件直接發布網站。Task 14 沒有建立 remote repository、沒有 push、沒有啟用 Pages、沒有 dispatch workflow，也沒有部署。

## 預期位置

- Owner：尚未決定；優先評估課程專用 GitHub Organization，不把它默認成個人網站的一部分。
- Repository 名稱：尚未決定。
- 預期 project-site URL pattern：`https://<owner>.github.io/<repository>/`

既有 owner-site repository 不在本專案範圍內，不得改名、覆蓋、force-push、搬移內容或改用本 artifact。

## Workflow 安全閘門

`.github/workflows/pages.yml` 在 main 的 Portal 相關變更上只 build、test、verify 與 upload artifact。`deploy` job 只有在維護者手動執行 `workflow_dispatch` 且明確把 `deploy` 設為 `true` 時才會運作。

- Build job：只有 `contents: read`。
- Deploy job：只有 GitHub Pages 必要的 `pages: write` 與 `id-token: write`。
- 沒有 repository secret、PAT、cloud credential 或第三方 deployment token。
- Base path 取自 `github.event.repository.name`；site origin 取自 `github.repository_owner`。
- Artifact 固定來自 `apps/portal/dist`，deploy job 只接受前一個 job 上傳的 Pages artifact。

GitHub 官方的 custom workflow 流程是 checkout、build、`upload-pages-artifact`、`deploy-pages`；deploy job 需要 Pages/OIDC 權限並建議使用 `github-pages` environment：

- <https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>
- <https://github.com/actions/upload-pages-artifact>
- <https://github.com/actions/deploy-pages>

## 本機 dry run

```sh
ASTRO_BASE_PATH=/repository-name \
ASTRO_SITE_URL=https://organization.github.io \
npm run build:public --workspace @calculus/portal

npm run verify:public --workspace @calculus/portal -- \
  /repository-name/

npm run verify:pages --workspace @calculus/portal
```

`verify:public` 檢查必要頁面、`zh-Hant`、base-safe links、已知 internal identifier，並要求 `/access/`、`/team/`、`/settings/`、`/sqlite-lab/`、`/components/`、`/scenarios/` 全部不存在；`verify:pages` 檢查手動 deploy gate、最小 job permissions、無 secrets、artifact path 與 Pages Actions。

## 尚待人工授權與操作

以下每一步都會改變外部狀態，本任務沒有執行：

1. 確認 GitHub owner、repository 名稱、repository visibility 與是否允許公開 fixture portal。
2. 確認既有 owner site 不受影響；新建不同名稱的 project repository。
3. 在建立 remote 前完成 Task 29 privacy/security review 與 Task 33 final go/no-go。
4. 由 repository 管理者建立 remote，設定 default branch 與必要 branch protection，再 push 經審查的 commit。
5. 在 repository `Settings → Pages → Build and deployment` 將 Source 設為 `GitHub Actions`。
6. 檢查 `github-pages` environment，限制 default branch，視需要加入 required reviewer。
7. 先觀察 push 觸發的 build-only workflow；確認 artifact 與 base-path verifier 全過。
8. 由有權限的維護者手動 Run workflow，把 `deploy` 設為 `true`。
9. 檢查首頁、加入、單案查詢、指南、404 與 `_astro` assets 都位於 repository base path；reviewer／封存 routes 不得出現在 public artifact。
10. 設定監控、撤回／停用方式與 responsible owner；若發現敏感資料，立即 unpublish 並撤除不當 artifact。

## Custom-domain migration note

先維持 project-site URL；不要在 prototype 階段寫入 `CNAME` 或修改 DNS。若日後另行核准 dedicated custom domain：

1. 先在 GitHub owner 設定驗證網域，降低 domain takeover 風險。
2. 先在 repository Pages settings 加入 custom domain，再修改 DNS；GitHub 官方警告反向順序會增加 takeover 風險。
3. GitHub Actions publishing 不需要 repository 內的 `CNAME`；custom domain 以 Pages settings/API 管理。
4. Dedicated custom domain 通常以 `/` 為 base；部署前把 `ASTRO_SITE_URL` 改為正式 HTTPS origin、`ASTRO_BASE_PATH` 改為 `/`，重新 build/verify。
5. 若只是沿用 owner site 已有 custom domain 的 project path，仍保持 `/<repository>/` base，不要誤改為 `/`。
6. DNS 不使用 wildcard record；完成解析與憑證後才開啟 Enforce HTTPS。
7. 保留回復至 `https://<owner>.github.io/<repository>/` 的計畫，並記錄 DNS/Pages rollback owner。

GitHub 官方 custom-domain guidance：

- <https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages>
- <https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site>
