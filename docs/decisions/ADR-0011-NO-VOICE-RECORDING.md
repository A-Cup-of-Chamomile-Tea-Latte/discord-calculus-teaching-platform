# ADR-0011: 第一版不錄音或自動語音轉錄

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: 教學團隊、隱私負責人
- Related tasks: 05, 20, 29, 31

## Context

語音 office hour 可支援互動，但錄音／轉錄會增加同意、旁觀者、保存、安全與錯誤文字紀錄等風險，且不是降低文字提問門檻的必要條件。

## Decision

第一版可使用 Discord 語音互動，但系統不錄音、不下載音訊、不啟動自動轉錄，也不建立相關資料欄位或權限。

## Consequences

### Positive

大幅降低敏感生物／聲音資料與未預期蒐集風險，縮小原型範圍。

### Negative

語音說明不會自動形成可搜尋紀錄；重要結論需由人員另行撰寫文字摘要並依一般內容規則處理。

### Operational

Bot permissions 不申請 voice receive/record capability。文件不得暗示語音被保存。

## Alternatives considered

自動轉錄或自願錄音能產生文字，但目前缺乏必要性與治理設計；只錄授課者也無法保證不收進學生聲音。

## Reversal strategy

若未來有明確教學需求，須新增 ADR、同意與保留政策、可見提示、存取控制及刪除流程，並在獨立試驗中實作；不直接擴充現有訊息 pipeline。

## Open questions

人工會後摘要的責任與格式可在教學流程文件中另訂，不影響本 ADR。
