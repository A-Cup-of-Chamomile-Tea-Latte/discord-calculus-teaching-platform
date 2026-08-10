# NAP BUILD 未決事項

> 歷史狀態：本文件是 2026-07-28 NAP BUILD 收尾快照。Discord 基建相關項目已由
> 2026-07-30 的實際佈建取代；現行未決事項以 `docs/NEXT_STEPS.md` 為準。

## 本輪重要未決

| 等級 | 事項                                                                                 | 本輪處理                                                                                                 | 後續門檻                                                            |
| ---- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| P0   | Task 34 legacy lifecycle 與最新 48h＋48h workflow 不同                               | 保留相容 code，產生 drift warning，不假裝已遷移                                                          | online GPT／產品確認 migration 與資料相容策略                       |
| P0   | Working／Archive retention、deletion、backup、consent withdrawal 未核准              | data policy fail closed，禁止真實資料                                                                    | 指定 owners 並完成治理決策                                          |
| P0   | 真實 Portal access boundary 未建立                                                   | 只有 fixture 靜態站，無真實 case prebuild                                                                | authenticated one-case backend 與防枚舉審查                         |
| P0   | Discord role hierarchy、兩隻 Bot apps、Private Support visibility 未在隔離伺服器實測 | 只產生 plan／diff／rollback／checklist                                                                   | 新的 GO-APPLY 指令及真人在場測試                                    |
| P1   | 正式 Class → Module 對照與 final main tags 未取得                                    | config 明確標示 unresolved／not finalized                                                                | 課程團隊確認                                                        |
| P1   | Private Support reopen UX、200-channel threshold 後替代方案未決                      | 顯示現行 temporary-channel proposal                                                                      | 壓力與隱私審查                                                      |
| P1   | Email reminder 與 fallback 只有介面                                                  | 無寄信、無 provider                                                                                      | sender、quota、退信與 incident owner                                |
| P2   | 學生友善版是否正式採用                                                               | 提供 local comparison；建議課程正式版為預設                                                              | 使用者測試與無障礙複核                                              |
| P2   | npm audit 回報 `fast-uri` 3.1.3 high advisory                                        | 確認為 `@astrojs/check` → language-server → YAML tooling 的 transitive dev-only dependency；未進靜態產物 | 上游釋出相容更新後升級並重跑 lockfile/check；不盲目 `npm audit fix` |

## 已處理但需留意

- `server.yaml` 使用 JSON-compatible YAML，避免新增 PyYAML 依賴；JSON 是 YAML 1.2 的合法子集。
- 最新設定包與三年比較包只作唯讀來源；沒有把 raw messages、姓名、ID、Email、附件或 Private Support 送入聊天、Git、公開 ZIP 或 LLM。
- `Administrator` 是人類治理角色名稱，但 Bot permission validator 永遠拒絕 `ADMINISTRATOR`。
- Config Studio 的 REMOVE 只是 diff 顯示；fake apply 只操作 `fixture_` stable keys，且保留 unmanaged resources。
