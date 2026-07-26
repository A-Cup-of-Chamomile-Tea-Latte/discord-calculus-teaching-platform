# ADR-0009: 一般案件以案件編號公開查詢

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: 教學團隊、Portal 維護者
- Related tasks: 07, 12, 17

## Context

網站代送的一般問題需要不依賴開啟 Discord 的進度入口。案件編號可供人閱讀，但若回傳過多資料或可枚舉，會形成資訊揭露風險。

## Decision

入口首頁提供單一 case number 查詢，只適用一般案件。Response 採最小公開欄位、明確 not-found／not-public 行為與可設定 prefix；內部 ID 與顯示編號分離。

## Consequences

### Positive

學生可低摩擦確認處理進度，網站代送流程有可追蹤回饋。

### Negative

可讀編號可能被猜測；即使內容公開，狀態與標題仍可能洩露不必要資訊。

### Operational

Adapter 必須先檢查 case type 與 visibility，再投影公開欄位。正式 rate limit、編號 entropy、cache 與公開欄位需隱私 technical spike。

## Alternatives considered

要求登入能降低枚舉，但增加進入門檻；只提供 Discord link 排除不想開 Discord 的使用者；不可讀 UUID 不利人工溝通。

## Reversal strategy

保持 case number 與 internal ID 分離。未來可加查詢 PIN、登入或 signed link，而不改案件主鍵與 bot mapping。

## Open questions

正式 prefix、編號生成方式、可公開標題／摘要及 rate limit 尚未核准。
