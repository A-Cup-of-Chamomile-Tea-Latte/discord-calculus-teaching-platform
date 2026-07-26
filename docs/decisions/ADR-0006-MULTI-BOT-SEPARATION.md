# ADR-0006: 多 bot 責任分離

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: Bot 維護者、系統維護者
- Related tasks: 20–25

## Context

互動／寫入、歷史讀取／匯出及未來 moderation 需要不同權限與事件所有權。以單一高權限 token 處理所有工作會擴大洩漏與誤操作影響。

## Decision

劃分 `course_assistant`（互動與寫入）、`archive_reader`（選定 thread 的讀取／匯出）與未實作的 `moderation` placeholder，並共用不含 token 的 `bots/common`。每個實際 bot 有獨立 application/token 與最小權限。

Task 20補充固定：

- `course_assistant`是唯一interaction/Discord write/role/nickname owner；baseline不要求Message Content intent。
- `archive_reader`只接受explicit selected-thread fetch，channel permissions只有allowlisted View Channel + Read Message History；為讀content/embeds/attachments申請自己的Message Content capability，但不訂閱message events、不註冊commands、沒有write/role/nickname methods。
- `moderation`在v1沒有application、token、permission、intent、event或service method。
- Token/config/runtime分離；共同library不能讀取或保存兩個token。
- Portal/browser不得直接呼叫Discord REST；Portal/GAS到bot的正式transport延後Task 32決策，暫以authenticated command API/queue作preferred direction而非accepted deployment。
- Event與command registry每項只有一個owner，以operation/interaction ID及durable idempotency避免duplicate side effects。

## Consequences

### Positive

權限與失敗範圍較小，事件所有權、audit 與部署可獨立說明。

### Negative

需要管理多個 application、設定與生命週期；錯誤的事件分工可能造成重複回應。

### Operational

不得以同一 token 啟動互相競爭的 process。完整矩陣、service ports、failure isolation及single-bot reversal constraints見`bots/ARCHITECTURE.md`與`docs/architecture/BOT_SERVICE_INTERFACES.md`；deployment topology仍需technical spike，原型只用fake client。

## Alternatives considered

單一 bot 較簡單，但要求更廣權限；同 token 多 process 除非明確 sharding，否則事件 ownership 不安全。

## Reversal strategy

各 bot 經共用 service interfaces 呼叫核心流程。若營運證據顯示分離成本過高，可在新 ADR 下合併 process，但仍保留 capability boundaries 與 least-privilege 檢查。

## Open questions

正式host數、Portal/GAS transport、Private Support Discord mechanism，以及course assistant是否確實需要privileged Guild Members intent仍未核准。第一版不啟用moderation。
