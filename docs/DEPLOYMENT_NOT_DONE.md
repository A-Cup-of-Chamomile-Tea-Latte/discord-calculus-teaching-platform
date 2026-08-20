# 部署邊界：已完成項目與未完成關卡

> 檔名為了不破壞既有連結而保留。本文已更新為 2026-08-19 的現況，不再把整個專案描述成純本機 mock。

## 現況

這個專案已有一部分外部服務在受控範圍內運作，但仍不是完成正式驗收的課程服務。

- allowlisted Discord Guild 已套用頻道與角色；Mac 上的 `course_assistant`、`dump_bot` 各有一個 live process。
- 本機 SQLite 是唯一 operational authority。
- `Server Database` 已套用 10-tab 精簡 schema；Standalone GAS 採 owner-only Execution API。
- Desktop OAuth 與虛構案件的 Local → Cloud projection，以及 Cloud → Local → Cloud command
  claim／apply／ack／duplicate-safe round-trip 均已通過。
- External／Testing OAuth 仍有約 7 天 refresh-token 生命週期；長期模式尚待 owner 選擇。
- Portal、email、正式身分驗證、remote 24h host、live cutover 與學生試用尚未完成。

完整收據見 [實作狀態](IMPLEMENTATION_STATUS.md) 與 [`project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md`](../project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md)。

## 元件狀態

| 領域 | 現況 | 下一個必要 gate |
| --- | --- | --- |
| Discord | 測試 Guild 與兩隻 Mac bots 運作中 | 正式試用範圍、權限複核與事故聯絡人 |
| SQLite | migration v5；案件與 outbox 同 transaction；live DB 唯讀 copy recovery rehearsal PASS | remote backup／restore rehearsal |
| GAS／Sheets | 5 個人用頁、5 個機器頁；owner-only 雙向 `scripts.run` smoke PASS | 決定 OAuth 長期模式；remote heartbeat 穩定後才啟用狀態摘要 trigger |
| Linux host | systemd、audit、backup 與 cutover tooling 已入庫 | SSH username、Tailscale target、host-key fingerprint |
| Portal | Astro fixture demo 與 UI 可用 | authenticated backend、查詢授權與 abuse controls |
| Email／身分 | domain logic 與 mock tests | 正式 provider、身分依據、rate limit 與保留政策 |
| Private Support | 分流與 deny-by-default 規則已有 | 正式受保護機制、ACL regression 與保留政策 |
| 教學分析 | 不在自動流程 | 學生同意、去識別化、人工 release gate 與核准目的 |

## 不可跳過的關卡

1. 授課教師／課程 owner 核准試用範圍、責任人與備援流程。
2. 決定資料告知、同意、撤回、保留、刪除、附件與 Private Support 規則。
3. 完成 Portal 查詢的 AuthN／AuthZ、rate limit、Private Support 隔離與一般錯誤回覆。
4. 取得並核對 remote host 身分，先做唯讀 audit 與 staging；未收到精確 `GO-LIVE-CUTOVER` 前不得停止 Mac writer。
5. 在 Google Auth Platform 決定 Production，或明確接受 Testing 模式約每 7 天人工重授權。
6. 在 remote staging 完成真實 Google smoke、SQLite backup／restore 與 one-writer 驗證。
7. live cutover 後按實際時間完成 24 小時觀察，再決定是否進入小規模試用。

## 外部狀態變更規則

建立 remote、公開網站、擴大 GAS access、啟用 email、移轉 live SQLite、停止 Mac bots 或開放學生試用，都需要各自的明確授權。既有 OAuth 與 Sheet 驗證不會自動解除其他 gate。

## 發現不當資料時

- 停止相關表單、匯出、匯入或 live test，不把原文貼入 issue、chat 或報告。
- 只記資料類別、位置、時間與處理狀態，不複製敏感值。
- 隔離本機 artifact；若已公開，由授權 owner 停用連結、撤銷 token 或更換憑證。
- 保留必要的 metadata-only audit，再依治理流程決定刪除與通知。

本文件不是法律意見、機構核准或 production sign-off。
