# DC Platform Beta 上線分工

更新日期：2026-08-27

這份清單分開記錄目前可完成的 Portal 工作、v13 之後的後端工作，以及數學系與朋友主機需要負責的部分。尚未完成本機驗收前，不拿未定案的伺服器設定請系辦代為測試。

## 現在可以完成

- 公開網站維持首頁、加入、案件查詢、使用指南與 404 五頁。
- Header 顯示「測試版 Beta」，公開頁與管理員頁分開建置。
- 加入頁優先推薦 Discord APP，另提供官方網頁版備援與簡短疑難排解。
- 課程邀請由 `PUBLIC_DISCORD_INVITE_URL` 注入，只接受 Discord 官方 HTTPS 邀請網址。未設定時不顯示假邀請按鈕。
- 加入與案件查詢 endpoint 未設定時維持 fail closed，不用 fixture 冒充成功。
- 公開 artifact 執行路由 allowlist、敏感字串、base path 與內部頁洩漏檢查。

正式邀請碼、數學系路徑與後端網址都屬於部署資料，不寫死在原始碼。

## v13 之後才能完成

1. **Email 額度排程**
   durable SQLite outbox 與 provider adapter 已有本機 journey；仍需在寄送額度不足時先保存申請意向，取得名額後才建立驗證碼與到期時間。額度用完時顯示實際排程日期，使用者不用重填。
2. **正式寄信驗收**
   Owner-only GAS `MailApp` 已完成單封實寄、收件內容、驗碼、去重與 outbox 清除驗收。正式 rollout 前仍須補齊 production 監控、退信處理與配額耗盡排程；目前先以一般 Gmail 的每日剩餘配額為硬上限，不宣稱可承受大量同時註冊。
3. **正式加入流程**
   Portal 寫入 SQLite，Course Manager 查找 Discord 成員，審核後套用角色並由 Bot 私訊結果。
4. **重設資料**
   支援更換班級、註冊信箱與 Discord 帳號；敏感變更需重新驗證並留下管理紀錄。
5. **Beta 開放控制**
   系統管理員可開啟 30 分鐘測試註冊、提前關閉，或開啟長期 Beta。這是應用程式權限，不以頁面上的假按鈕代替伺服器檢查。
6. **正式 API 與身分**
   接上 HTTPS backend、session、CSRF、rate limit、稽核紀錄與管理員授權，再做學生、訪客、助教與系統管理員的白帳號端到端測試。
7. **部署與復原**
   完成 production backup rehearsal、版本升級、smoke test 與 rollback，通過後才開放真實申請。

## 各方要負責什麼

| 對象 | 要負責的工作 | 不需要負責 |
| --- | --- | --- |
| 本專案 | Portal、API、Bot、Email queue、測試、部署包與操作文件 | 不把未驗證需求丟給系辦試錯 |
| 數學系網管 | 建立 `~calc/DC-platform-beta/`、提供靜態檔更新方式，並告知是否允許該路徑連到外部 HTTPS API | 不維護 SQLite、不保管 Discord token、不修改課程程式 |
| 朋友主機 | 執行 Portal backend、Bot、SQLite、Email worker，提供 HTTPS、備份與服務監控 | 不對外公開 SQLite 檔案或管理憑證 |
| 系統管理員 | 開關 Beta、審核教學團隊、處理例外、查看 queue 與稽核結果 | 不逐筆手動寄驗證碼 |

## 何時跟系辦談

先完成下列項目，再寄出需求：

- v13 本機端到端流程與單封 GAS 實寄通過。
- 靜態部署包可以在 `/~calc/DC-platform-beta/` 正常顯示。
- 外部 API 直連與路徑轉送兩種方案都在本機模擬完成。
- 已有固定的後端 HTTPS 網域、健康檢查與測試帳號。
- 清楚列出系辦只要回答的問題，不要求對方共同設計系統。

屆時第一封信只問三件事：該目錄如何更新、是否允許將限定的 API 路徑連到外部 HTTPS 服務、網管需要我們提供哪些測試資料。若不允許路徑轉送，就改採瀏覽器直接連外部 API 的備案，不反覆要求系辦調整伺服器。

## 免費 Google 帳號的瓶頸

目前預定的 `ntusupercool@gmail.com` 是一般 Gmail。Google 公開配額顯示：

- Apps Script `MailApp`：一般帳號每日 100 位收件者；Workspace 每日 1,500 位。
- 一般 Gmail 帳號的標準寄信限制約為每日 500 封或收件者；Gmail API 仍受該帳號的標準寄信限制。

因此，現行 GAS `MailApp` 路線不能直接採用「專案每日 400 封」。若要自動寄 400 封，必須改用經 OAuth 授權的 Gmail API，或取得可用的 Workspace／課程帳號，並先做小批實寄。免費帳號的限制還可能因退信或 Google 防濫用機制提早生效，程式不能把 500 寫成保證值。

若 provider 實測可用 500 封，可先把專案上限設為 400 封：320 封首次驗證、40 封重寄、20 封資料重設、20 封失敗重試；另外 100 封留給帳號本身與人工處理。若仍用 `MailApp`，則改為 80、10、5、5，並接受首次大量加入需要分批消化。

每次寄送前都要讀取剩餘配額。系統達到上限後保留申請，顯示下一個預定寄送批次；管理員只需暫停、恢復或處理整批，不逐筆輸入驗證碼。

官方資料：

- [Apps Script 配額](https://developers.google.com/apps-script/guides/services/quotas)
- [Gmail 寄送限制](https://support.google.com/mail/answer/22839)
- [Gmail API 限制](https://developers.google.com/workspace/gmail/api/guides/handle-errors)
