# ADR-0010: Private Support 分離保護

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: 教學團隊、隱私負責人、系統維護者
- Related tasks: 07, 13, 25, 27, 29

## Context

敏感求助的可見性、處理人員與後續用途不同於一般課程討論。僅把一般案件標為「匿名」不足以防止公開查詢、匯出或權限錯誤。

## Decision

Private Support 使用獨立 case type、入口、storage/Discord access policy 與 response projection。它不出現在公開 case-number search，且 analysis permission 預設 `EXCLUDED`。正式 private Discord mechanism 未驗證前只用 restricted backend/mock。

## Consequences

### Positive

最小化誤公開與誤匯出，讓學生與教學團隊能清楚理解保護界線。

### Negative

流程與權限測試較多；Discord private thread、restricted text channel 或純後端方案各有限制。

### Operational

所有 adapter 採 deny-by-default，contract tests 驗證公開 lookup 永不回傳 Private Support。正式 Discord 權限與 audit 需 technical spike。

## Alternatives considered

與一般案件共用相同 channel／search 再靠 flag 過濾較簡單，但單點錯誤即可洩露；「匿名公開」也無法提供相同保護。

## Reversal strategy

保留獨立 type 與 policy interface；可在不改 Portal contract 的情況下替換 private Discord mechanism，或完全移到受控 backend。

## Open questions

可存取角色、緊急升級流程、保留／刪除期限及正式 mechanism 均待治理與 technical spike。
