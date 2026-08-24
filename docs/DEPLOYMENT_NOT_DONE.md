# 部署邊界：已完成項目與未完成關卡

> 檔名為了不破壞既有連結而保留。本文已更新為 2026-08-24 的現況；最新細節以
> [實作狀態](IMPLEMENTATION_STATUS.md) 為準。

## 現況

這個專案已有一部分外部服務在受控範圍內運作，但仍不是完成正式驗收的課程服務。

- allowlisted Discord Guild 已套用頻道與角色；Remote Linux 是唯一 production writer，Mac writers 已停止。
- Remote SQLite 是唯一 operational authority；production schema 為 v6。
- `Server Database` 已套用 10-tab 精簡 schema；Standalone GAS 採 owner-only Execution API。
- Desktop OAuth 與虛構案件的 Local → Cloud projection，以及 Cloud → Local → Cloud command
  claim／apply／ack／duplicate-safe round-trip 均已通過。
- Google Auth Platform 已切到 External／Production；owner credential 可 refresh 並通過 owner-only `scripts.run`。
- Remote cutover 已完成；現行 v6 baseline 的 24 小時 observation 已於 2026-08-24 17:16 PASS。
- Portal backend、email、正式身分 authority 與學生試用仍未完成。

完整收據見 [實作狀態](IMPLEMENTATION_STATUS.md) 與 [`project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md`](../project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md)。

## 元件狀態

| 領域 | 現況 | 下一個必要 gate |
| --- | --- | --- |
| Discord | Remote 三服務 production baseline v6；repository 有尚未部署的 Bot candidate v10 | production 設定映射、白帳號 ACL regression 與另行部署 gate |
| SQLite | production v6；repository v10；schema-shaped v6 暫存副本的 v6 → v10 rehearsal PASS | production consistent backup rehearsal 與另行 deploy 授權 |
| GAS／Sheets | 5 個人用頁、5 個機器頁；owner-only 雙向 `scripts.run` smoke PASS | candidate release 前安全核對；status digest 另行決定 |
| Linux host | systemd cutover 完成；remote 是唯一 writer；v6 observation PASS | candidate forward gate |
| Portal | 公開／reviewer artifact 分離；public 未接線功能 fail closed | same-origin backend、查詢授權與 abuse controls |
| Email／身分 | domain logic 與 mock tests | 正式 provider、身分依據、rate limit 與保留政策 |
| Private Support | 分流與 deny-by-default 規則已有 | 正式受保護機制、ACL regression 與保留政策 |
| 教學分析 | 不在自動流程 | 學生同意、去識別化、人工 release gate 與核准目的 |

## 不可跳過的關卡

1. 授課教師／課程 owner 核准試用範圍、責任人與備援流程。
2. 決定資料告知、同意、撤回、保留、刪除、附件與 Private Support 規則。
3. 完成 Portal 查詢的 AuthN／AuthZ、rate limit、Private Support 隔離與一般錯誤回覆。
4. 以 production v6 consistent backup 的獨立副本演練 repository candidate v10，核對 backup readability、integrity、ledger、row counts 與 rollback。
5. 完成 production Discord 設定與白帳號端到端驗收；任何 candidate deploy 需另行明示授權。
6. 新 release gate 通過後，才決定是否進入小規模試用；CNAME、公開網址與 rollout 可稍後處理。

## 外部狀態變更規則

公開網站、擴大 GAS access、啟用 email、升級 production SQLite／Bot release 或開放學生試用，都需要各自的明確授權。既有 cutover、OAuth 與 Sheet 驗證不會自動解除其他 gate。

## 發現不當資料時

- 停止相關表單、匯出、匯入或 live test，不把原文貼入 issue、chat 或報告。
- 只記資料類別、位置、時間與處理狀態，不複製敏感值。
- 隔離本機 artifact；若已公開，由授權 owner 停用連結、撤銷 token 或更換憑證。
- 保留必要的 metadata-only audit，再依治理流程決定刪除與通知。

本文件不是法律意見、機構核准或 production sign-off。
