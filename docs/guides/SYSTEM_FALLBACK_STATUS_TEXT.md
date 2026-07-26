# 系統狀態與 fallback 文案庫（草案）

本文案庫供 Portal、學生通知與助教 SOP 對齊。不應把 prototype 的「未連接」誤報為正式服務故障，也不應在沒有即時監控時顯示「一切正常」。

| 情境                   | 建議標題                       | 建議內文／下一步                                                                                |
| ---------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------- |
| Fixture prototype      | 原型模式：未送出真實資料       | 本頁只使用虛構資料示範。表單不會寄信、發 Discord 訊息或寫入 Sheets。                            |
| 案件查詢無結果         | 找不到這個一般案件             | 檢查編號格式後再試一次。Private Support 不會出現在公開查詢；請使用受保護連絡方式。              |
| 案件 adapter 不可用    | 目前無法取得案件狀態           | 請稍後以明確重新整理再試。系統不會在背景持續重試；正式課務資訊以 NTU COOL 為準。                |
| 表單後端不可用         | 這次內容尚未送出               | 請保留自己的非敏感文字，並使用課程已公告的備援管道。不要重複送出 Private Support 內容到公開區。 |
| Discord 不可用         | Discord 目前不可作為提問管道   | 課務資訊以 NTU COOL 為準；提問請改用課程已公告的備援管道。                                      |
| Private Support 不可用 | Private Support 管道目前不可用 | 請勿把敏感內容改貼到公開 Discord 或一般案件。使用課程已公告的受保護連絡方式。                   |
| Email 驗證延遲         | 驗證信尚未送達                 | 請先檢查輸入與垃圾郵件。避免連續重送；驗證失敗不應暴露信箱是否已存在。                          |
| 本機 export 失敗       | 匯出尚未完成                   | 請勿將 partial files 送往分析或匯入。檢查 manifest/hash/schema，再由授權管理者重新完整 dump。   |
| 去識別化待複核         | 尚未通過人工隱私複核           | 不得匯入、公開或交給 AI。請完成 review checklist 並處理 residual identifiers。                  |
| 疑似資料外洩           | 服務已停止以進行資料保護       | 不要在公開管道複製受影響內容。授權 owner 應先停用受影響 artifact/credential，再依事故流程處理。 |

## 狀態頁最少要素

- 最後人工更新時間與 timezone。
- 明確說明是 manual status，不是 SLA 或即時監控。
- Portal、case adapter、Discord、GAS/Sheets、email 分開顯示，不用單一「系統正常」包含所有外部依賴。
- 每個 error/empty 狀態都有不需猜測的下一步。
- 不在 status text 放入未審核的正式 URL、負責人電子信箱、token 或 internal IDs。
