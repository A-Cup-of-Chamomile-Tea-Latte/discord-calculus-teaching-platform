# 詞彙表

本文件統一產品與技術文件用語。除非另有註明，英文識別字是程式／契約用語，學生介面應使用旁列繁體中文。

| 詞彙                                                | 定義與邊界                                                                                                                                                                                                                     |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **NTU COOL**                                        | 本課程教材、作業、成績、期限、正式公告與課程政策的正式依據。Discord 與入口網站只能補充，不能取代它。                                                                                                                           |
| **入口網站（portal）**                              | 學生與教職員使用的輕量網站，提供 onboarding、Discord 指南、隱私說明與一般／Private 單案最小狀態查詢。它不代收題目或附件，也不直接持有 Discord bot token。 |
| **案件（case）**                                    | 對一個需要追蹤的提問或求助所建立的結構化紀錄，有內部 ID、顯示用案件編號、類型、狀態、可見範圍、作者顯示方式與外部 thread 映射。案件不等同於單一訊息。                                                                          |
| **案件編號（case number）**                         | 格式為 `Cxx-<六字元安全亂數>-MMDD-HHMM[-P]` 的操作標籤，例如 `C12-7K4M2Q-0907-2007`。token 不從個資或 internal UUID 衍生；`C99` 與 `-P` 識別 Private Support。完整 Private 案號可查最小狀態，不是讀取內容的權限。 |
| **forum post**                                      | Discord forum channel 裡的一個主題貼文，通常會建立對應 thread。原型可把一個一般案件映射到一個 forum post/thread，但實際 Discord 行為仍需 technical spike。                                                                     |
| **thread**                                          | 圍繞某個主題的訊息串。可屬於 forum post，也可由其他 Discord 位置建立；匯出時需保留訊息順序、回覆、編輯與附件 metadata。                                                                                                        |
| **text channel**                                    | Discord 中可直接發送多則訊息的文字頻道，與 forum channel／thread 不同。Private Support 是否使用受限 text channel、private thread 或其他機制尚待驗證。                                                                          |
| **Private Support（私密支援）**                     | 與一般案件分開的受限 Discord 求助類型；只有授權人員可讀內容。Portal 可依完整案號顯示 content-free 狀態；逐案 AI 選擇會保存，但不會自動觸發匯出或 AI 傳輸。 |
| **課程代號（course alias）**                        | 伺服器中的課程顯示別名，格式為 `nnmmm`：兩位班別代碼加三位加入順序。它只是一種作者顯示方式，不能隱藏 Discord 全域帳號資料，也不能單獨證明課程身分。                                                                            |
| **作者顯示方式（author display mode）**             | 內容對一般讀者顯示作者的方式：真實姓名、課程代號、或對一般成員匿名但可由授權管理者識別。它與「誰能看到內容」分開。                                                                                                             |
| **可見範圍（visibility）**                          | 內容允許被班級、全課程或只有教學團隊看到的範圍。可見範圍不決定作者名稱如何顯示。                                                                                                                                               |
| **activation code / nonce（啟用碼／一次性隨機值）** | 提供給人工核准例外成員的單次、限時、可稽核憑證。內部只保存不可逆 verifier／hash 與狀態，不保存或回傳明文；兌換後立即失效。                                                                                                     |
| **OAuth2**                                          | 讓使用者授權入口網站綁定 Discord account，並可能授權加入 server 的標準流程。它證明 Discord 授權，不等同於 NTU email 驗證或課程 membership。                                                                                    |
| **email 驗證**                                      | 證明使用者控制所填 email 的流程。NTU Mail 可支援機構身分判斷；Gmail 可作選填聯絡方式，但兩者用途不可混為一談。                                                                                                                 |
| **fixture（測試資料）**                             | 穩定、可重現、人工設計且完全虛構的資料，用來讓 Portal、GAS、bots 與 tools 在沒有正式服務時共同測試。fixture 必須可提交且不得含真實個資或 secrets。                                                                             |
| **mock（模擬實作）**                                | 在測試或原型中模擬外部服務行為的替身，例如假 email delivery。mock 不代表真實 API、配額或權限已驗證。                                                                                                                           |
| **adapter（介接層）**                               | 把產品流程與特定外部系統隔離的介面與實作，例如同一個 CaseLookup adapter 可有 fixture 版與未來 GAS 版。adapter 的目的是讓替換與測試更安全。                                                                                     |
| **dump（單次匯出）**                                | 管理者明確要求某一個選定 Discord thread 的完整快照，輸出 JSON/Markdown 與 manifest。它不是持續監控。                                                                                                                           |
| **follow（追蹤匯出）**                              | 管理者明確設定一個已選定 thread，之後以游標／時間點增量取得更新的流程。第一版只能在清楚的範圍、停止方式與同意規則下實作，不表示跟隨所有 server 對話。                                                                          |
| **analysis permission（教學分析同意）**             | 控制內容能否進入假名化教學品質檢視的帳號預設與逐篇 override。一般與 Private 案件都會記錄選擇；同意不會自動觸發傳輸，也不等同於同意公開、模型訓練或自動評分。 |
| **來源（source）**                                  | 紀錄由 `PORTAL`、`DISCORD`、`BOT` 或 `IMPORT` 產生，用於追蹤資料流；來源不是可信度或權限等級。                                                                                                                                 |
| **案件狀態（status）**                              | 固定為 `OPEN`、`TRACKED`、`IDLE`、`CLOSED`、`AUTO_CLOSED`。`REOPENED` 是事件，不是持久狀態；舊狀態只經相容轉換層讀取。                                                                                                         |
| **schema version**                                  | 每筆跨元件資料宣告的契約版本，用於驗證與相容性管理；不應與應用程式部署版本混用。                                                                                                                                               |

## 容易混淆的三組概念

1. **Discord OAuth2、email 驗證、course membership**：分別證明 Discord 授權、email 控制權及課程資格，不能互相取代。
2. **作者顯示方式、可見範圍、analysis permission**：分別回答「顯示誰」、「誰看得到」、「能否進入後續教學分析」。
3. **forum post、thread、text channel**：是不同的 Discord 結構；文件不得把三者當作同義詞。
