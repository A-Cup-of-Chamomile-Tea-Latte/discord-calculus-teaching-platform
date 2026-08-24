# Portal 託管準備度

狀態：`PUBLIC_ARTIFACT_VERIFIED / DEPLOY_REQUIRES_REVIEW`。

## 建議

第一階段可使用 GitHub Pages 的 project site，例如 `https://<account>.github.io/<repository>/`。它可以和既有的個人首頁 `https://<account>.github.io/` 共存，不必交給數學系主機；系網站日後只需放一個穩定入口連結。

目前 Portal 是 Astro static build，已有：

- project-site base path 支援；
- GitHub Actions build／test／artifact 工作流程；
- 只有人工 `workflow_dispatch` 且 `deploy=true` 才部署的閘門；
- 無 repository secret 依賴；
- `config/academic/**` 變更會觸發重新建置。
- `build:public` 會在上傳前套用公開 route allowlist；reviewer build 仍保留完整本機審查工具。

GitHub 官方說明 project site 會位於 `username.github.io/repository`；GitHub Pages 是靜態託管，不執行 PHP、Ruby 或 Python 等 server-side 語言。

參考：

- [Deploying a website automatically](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically)
- [Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)

## 流量判斷

以約 2,500 人總母體、先估 30% 使用、尖峰少於 2% 的靜態入口來看，前端流量不是主要風險。GitHub Pages 的公開限制包含 1 GB published site 與每月 100 GB soft bandwidth；真正需要優先處理的是動態註冊、OAuth、資料寫入與後端可用性，而不是這個 static shell。

參考：[GitHub Pages limits](https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/github-pages-limits)

## 已完成的公開邊界

公開 artifact 只保留首頁、加入、案件狀態查詢、合併後的使用指南與 404。`/access/`、`/components/`、`/sqlite-lab/`、`/scenarios/`、`/settings/`、`/team/`、`/status/` 會在 artifact 上傳前移除；舊 `/ask/`、`/private-support/`、`/discord-guide/` 與案件全文路由也不得出現。驗證腳本會在任一內部或封存頁殘留時失敗。

本機 reviewer build 仍保留上述頁面，讓教學團隊可以審查，不以刪除歷史功能換取公開安全。

## 公開前仍需決定

GitHub Pages 只能承載公開靜態前端。正式註冊、OAuth callback、Discord role 指派、case persistence 與任何敏感交易都必須放在另外的受保護 backend；GitHub 也明確提醒 Pages 不適合處理密碼或敏感交易。

因此目前的安全停止點是：

1. 可以在本機與 CI 建置／驗證 project-site artifact。
2. 不 dispatch deploy workflow。
3. 不將 reviewer artifact、任何本機身份資料或 Config Studio 公開。
4. 待 repository visibility、正式網址與 backend origin 完成人工審核，再發布。

## 其他選項

若之後需要同一平台承載輕量 API，可考慮 Cloudflare Pages + Workers；靜態 asset request 免費且不限量，Functions 則依 Workers quota 計費／限額。這不是現階段必要遷移。

參考：

- [Cloudflare Pages](https://developers.cloudflare.com/pages/)
- [Pages Functions pricing](https://developers.cloudflare.com/pages/functions/pricing/)

## Personal website 與 custom domain

已有 `github.io` 個人網站不會阻止建立 project site。若個人站使用 custom domain，project site 的網域與路徑繼承行為需要在發布前核對；想保持課程入口獨立時，可先用預設 project-site URL，或日後指定獨立子網域。

參考：[About custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages)
