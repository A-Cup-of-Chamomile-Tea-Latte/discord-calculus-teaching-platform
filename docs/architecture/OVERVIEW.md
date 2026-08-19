# 架構概觀

## 文件定位

本圖描述 2026-08-19 已驗證的架構與仍受 gate 限制的部分。它不是正式課程服務核准文件。最新執行狀態以 [實作狀態](../IMPLEMENTATION_STATUS.md) 為準。

## 現行資料路徑

```mermaid
flowchart LR
  student["學生"]
  staff["助教／教師"]
  cool["NTU COOL<br/>正式課務來源"]
  discord["Discord<br/>allowlisted Guild"]
  writer["course_assistant<br/>互動與案件寫入"]
  reader["dump_bot<br/>受控讀取與匯出"]
  sqlite["本機 SQLite<br/>唯一 operational authority"]
  outbox["可靠 outbox<br/>待投影工作"]
  bridge["data_bridge<br/>已實作，尚未 remote 常駐"]
  gas["Standalone GAS<br/>owner-only scripts.run"]
  sheet["Server Database<br/>5 個人用頁 + 5 個機器頁"]
  bound["Bound GAS<br/>管理選單與狀態摘要"]
  portal["Astro Portal<br/>目前 fixture mode"]
  clean["Consent + 去識別化<br/>人工複核"]

  student --> cool
  student --> discord
  staff --> discord
  discord <--> writer
  writer --> sqlite
  staff --> reader
  reader --> discord
  reader --> clean
  sqlite --> outbox
  outbox --> bridge
  bridge --> gas
  gas --> sheet
  bound <--> sheet
  student -. 尚未接正式後端 .-> portal
```

Mac 上的 `course_assistant` 與 `dump_bot` 已各以單一 LaunchAgent 實例運作。SQLite 的案件異動與 outbox 在同一個 transaction 寫入；Google 暫時不可用時，Discord 不必停寫，未完成投影仍留在本機。Standalone GAS 只接受 owner 的 Apps Script Execution API 呼叫，不提供公開 Web App endpoint。

Linux host、remote staging、live cutover 與 24 小時觀察仍未開始。上圖中的 `data_bridge` 已通過本機到真實 GAS／Sheet 的虛構案件 smoke test，但尚未成為 production 常駐服務。

## 元件與信任邊界

1. **正式課務邊界**：NTU COOL 仍是教材、成績、期限與政策的權威來源。Discord 與 Portal 只能補充教學互動。
2. **Discord 寫入邊界**：`course_assistant` 負責案件與互動寫入；`dump_bot` 只讀取管理者明確指定的範圍。兩隻 bot 不共用 token 或權限角色。
3. **本機資料邊界**：SQLite 是案件狀態的唯一權威來源。Sheet 是精簡投影，不能在沒有版本、checksum、來源與人工確認時反向覆寫本機。
4. **Google 邊界**：Standalone GAS 採 `executionApi.access=MYSELF`。OAuth 憑證只存於 Git-ignored、權限 `0600` 的本機目錄；GAS、Sheet 與報告不保存 client secret 或 refresh token。
5. **瀏覽器邊界**：Portal 目前只使用虛構資料。未完成 authenticated backend、rate limit 與 Private Support 隔離前，不得把真實案件打包進靜態 JavaScript 或開放一般查詢。
6. **分析與匯出邊界**：raw Discord 匯出只能留在受保護本機區。送往任何 AI 或分析流程前，必須通過同意判定、去識別化與人工複核；Private Support 預設排除。

## 為何保留 Astro Portal

Portal 使用 Astro、TypeScript 與 static output。它負責學生可閱讀的加入說明、隱私引導、查詢介面與本機教學頁，不承擔 bot token、SQLite writer 或 Google owner authority。正式後端尚未選定，因此目前仍維持 fixture mode，不把 `scripts.run` 暴露給瀏覽器。

## 關鍵交換契約

- `Case`／`CaseLookupResponse`：內部案件與公開 allowlist 投影分離。
- SQLite migration v5：案件 lifecycle、service health、projection stream 與可靠 outbox。
- `ProjectionEnvelope`：Bridge 的 preview／apply 契約，包含 schema 版本、來源與 checksum。
- `ExportManifest`／`ThreadExport`：管理者明確啟動的受控 dump／follow 紀錄。
- `SanitizedThread`：同意過濾、case-local pseudonym 與結構化 placeholder；仍須人工複核。
- `AuditEvent`：只記必要動作、結果與時間，不以任意 metadata 收藏敏感內容。

詳細元件表見 [CONTEXT.md](CONTEXT.md) 與 [COMPONENTS.md](COMPONENTS.md)；部署與 cutover 規則見 [production integration plan](PRODUCTION_INTEGRATION_PLAN.md) 與 [live cutover runbook](../ops/LIVE_CUTOVER_RUNBOOK.md)。
