# Portal 託管準備度

狀態：`PUBLIC_ARTIFACT_VERIFIED / DEPLOY_REQUIRES_REVIEW`。

## 建議

下一個 gate 是獨立 HTTPS synthetic staging，不是直接發布。staging 必須讓 static pages 與 `/api/` 位於同一 origin，並使用獨立 secret、synthetic SQLite、capture-only Email 與不可見的 production paths。

若數學系只能提供連結、不能提供同源 `/api/` reverse proxy，完整 Portal 可放在朋友主機的受控 HTTPS origin，由統一教學網提供穩定入口。GitHub Pages project site 只能作為純靜態／link-only 選項；它不能執行 current session issuer 或 backend，也不能和另一個 origin 的 API 組成 connected Portal。

目前 Portal 的 public shell 是 Astro static build，已有：

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
4. 待正式網址、backend origin、same-origin topology 與系網部署權限完成人工審核，再發布。

系網所需確認的完整介面與更新協議見 `../ops/DEPARTMENT_HANDOFF_GATE.md`。公開可觀察到的現行入口是 `https://www.math.ntu.edu.tw/~calc/Default.html`；這不代表 `/~calc/DC-platform-beta/` 已存在或已獲准，也不證明系網允許上傳、server runtime 或 reverse proxy。

## 其他選項

若之後需要同一平台承載輕量 API，可考慮 Cloudflare Pages + Workers；靜態 asset request 免費且不限量，Functions 則依 Workers quota 計費／限額。這不是現階段必要遷移。

參考：

- [Cloudflare Pages](https://developers.cloudflare.com/pages/)
- [Pages Functions pricing](https://developers.cloudflare.com/pages/functions/pricing/)

## Personal website 與 custom domain

已有 `github.io` 個人網站不會阻止建立 project site。若個人站使用 custom domain，project site 的網域與路徑繼承行為需要在發布前核對；想保持課程入口獨立時，可先用預設 project-site URL，或日後指定獨立子網域。

參考：[About custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages)
