# 元件責任表

| 元件                     | 負責                                                                           | 明確不負責                                                       | 主要資料／介面                                          | 尚待 technical spike                                           |
| ------------------------ | ------------------------------------------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------------- |
| NTU COOL                 | 正式教材、作業、成績、期限、公告與政策                                         | 社群問答；由本原型覆寫正式資料                                   | 本原型不自動同步                                        | 無，本專案只記平台邊界                                         |
| Astro Portal             | onboarding、隱私說明、可選代送、一般案件單筆查詢、Private Support 入口         | 持有 secrets；公開私密案件；取代 NTU COOL                        | CaseLookupResponse、forms adapters                      | Pages base path、CORS、正式 OAuth callback                     |
| Case/onboarding adapters | 驗證 request、投影最小 response、隔離 mock/GAS                                 | 直接暴露 sheet row 或 bot token                                  | JSON contracts                                          | AuthN/AuthZ、rate limit、CORS                                  |
| Apps Script admin API    | 少量原型／行政資料操作與 audit                                                 | 高頻逐訊息儲存；資料上傳工具角色的 clasp                         | SheetsStorage adapter、batch endpoint                   | quotas、LockService、Web App 權限                              |
| Google Sheets            | 原型 users、memberships、consents、case index、audit                           | 原始 Discord 即時 mirror、正式高頻資料庫                         | 經 GAS 存取                                             | 欄位保護、備份、保留期限                                       |
| course_assistant         | 唯一Discord interactions與授權寫入owner、匿名內容代貼、核准的role/nickname操作 | 全server匯出；直接分析；Message Content監看；保存/共用token      | `CourseAssistantService`、narrow writer port            | member intent需求、modal/forum行為、rate limits                |
| dump_bot           | 只讀管理者明確選定的allowlisted thread                                         | 持續監看全部server；commands；send/role/nickname/status mutation | `ArchiveReaderService`、narrow reader port、CaseMessage | Message Content核准、history/attachment pagination/rate limits |
| moderation placeholder   | 保留未來責任空間                                                               | 第一版application/token/permission/intent/event/service          | 無                                                      | 若要啟用須新ADR與privacy review                                |
| Explicit export tool     | dump/follow 選定 thread、產生 JSON/Markdown/manifest                           | 自動送往 AI；提交真實匯出到 Git                                  | ExportManifest、CaseMessage                             | incremental cursor、附件策略                                   |
| Consent/anonymizer       | 套用帳號／逐篇同意與假名化規則                                                 | 宣稱不可逆匿名；納入 Private Support 預設資料                    | Consent、ExportManifest                                 | 撤回、保留與風險測試                                           |
| Sheets importer          | 驗證後批次送出                                                                 | 逐訊息同步；以 clasp 代替 upload                                 | batch manifest、storage adapter                         | retry、idempotency、quota                                      |
| Contracts/fixtures       | 跨語言 schema、有效／無效範例、虛構回歸資料                                    | 框架內部物件、secrets、真實學生資料                              | JSON Schema                                             | Task 07/08 落實                                                |
| Email adapter            | 模擬驗證信 delivery 結果                                                       | Task 19 前寄送真信；保存 mailbox credential                      | delivery interface                                      | provider、rate limit、退信處理                                 |

## 跨元件規則

1. 外部平台只能透過 adapter 或 bot boundary 存取。
2. 作者顯示方式、可見範圍與 analysis permission 是三個獨立欄位。
3. 公開 query 在資料投影前先檢查 case type；Private Support deny-by-default。
4. 原始訊息只由明確匯出流程取得，Sheets 僅接收經驗證的批次資料。
5. Contracts 變更先更新 schema、範例與 contract tests，再調整消費者。
6. 每個Discord capability/event/command只有一個primary owner；共同code不代表共同credential。
7. Browser永不持有bot token；Portal/GAS→Discord transport在Task 32前維持fixture port與未決狀態。
