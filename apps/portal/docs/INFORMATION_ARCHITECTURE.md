# Portal information architecture

更新日期：2026-08-24

## 產品定位

Portal 是公開、輕量的課程入口。它負責加入申請、Discord 使用說明與最小案件狀態查詢；提問、圖片、回覆、隱密空間與通知由 Discord／Course Manager 負責。SQLite 仍是 operational authority，瀏覽器不得成為 writer 或持有 Bot、Google、OAuth secrets。

## 現行路由

| 路由                   | 對象     | 負責                                      | 不負責                                |
| ---------------------- | -------- | ----------------------------------------- | ------------------------------------- |
| `/`                    | 公開     | 課程入口、平台分工、案件查詢              | 收題目、顯示案件內容                  |
| `/join/`               | 公開     | 學生／訪客加入申請 shell                  | 直接核發 Discord 權限                 |
| `/cases/`              | 公開     | 一般／隱密案件的最小狀態查詢              | 題目、對話、作者、附件、AI 或管理操作 |
| `/guide/`              | 公開     | 公開／隱密提問、隱私、同意與 FAQ          | 取代各班 NTU COOL                     |
| `/404.html`            | 公開     | 安全返回入口                              | 由 URL 猜測案件是否存在               |
| `/access/`             | reviewer | 本機內部身份入口                          | 正式 server-side authorization        |
| `/team/registrations/` | reviewer | Course Manager 加入審核骨架               | 未接線前執行 Discord role write       |
| `/status/`             | 管理員   | 建造 gate；完成後轉長期 monitor dashboard | 對外公開 owner diagnostics            |

## 已封存路由

`/ask/`、`/private-support/`、`/discord-guide/` 只留 reviewer build 的封存提示，不進公開 artifact。`/cases/[caseNumber]/` 已移出路由樹；網頁不再呈現案件全文。封存對照見 `docs/archive/portal-pre-architecture-2026-08-24/README.md`。

## 公開／內部 artifact

公開 build 只允許首頁、加入、查案件、合併指南與 404。內部登入、審核工具、狀態、元件、情境與舊路由必須由 build script 實際移除，不能只靠導覽隱藏。

## 動態邊界

- 加入申請：未來送往受保護 backend，進入 Course Manager 審核佇列；公開靜態 build 在 endpoint 未設定時停用送出。
- 案件查詢：未來只接受單一完整案號並回傳 allowlisted status projection；不列出案件、不背景 polling。
- Discord：公開提問直接發文；隱密支援由指令建立受限空間。附件留在 Discord，不經 Portal 上傳。
- Browser：不得直接讀 SQLite、呼叫 Discord REST、持有 Bot token 或打開 owner-only GAS endpoint。
