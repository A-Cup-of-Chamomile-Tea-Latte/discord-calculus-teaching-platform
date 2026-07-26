# ADR-0005: Discord bots 使用 Python + discord.py

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: Bot 維護者
- Related tasks: 20–25, 30

## Context

Bots 需要 interactions、modal、forum/thread 讀寫與可測試的非同步流程。團隊方向已指定 Python，且 `discord.py` 提供成熟的 Discord API abstraction。

## Decision

使用 Python 3.12–3.14 相容範圍與 project-local `discord.py`。bot-specific handler 與共用 contracts/config/logging 分離；foundation 階段不連正式 server。

## Consequences

### Positive

Python 適合本機資料工具，共用型別與測試慣例可降低維護成本。

### Negative

Discord intents、rate limits、interaction timeout 與 library 版本行為必須實測；同步阻塞操作會傷害 bot responsiveness。

### Operational

每個 bot 使用自己的 token、最小 intents 與權限。Token 只由 runtime environment 注入，不寫入 repository 或瀏覽器。

## Alternatives considered

discord.js 有良好生態，但會使 bot 與既有 Python export tooling 分裂；直接呼叫 REST/Gateway 則不必要地增加協議負擔。

## Reversal strategy

把 Discord calls 藏在 adapter/handler 邊界，核心 contracts 保持 JSON；未來可換 library 或語言，透過 contract tests 保持行為。

## Open questions

所需 intents、modal 限制、forum/thread API 行為及 Python 3.14 compatibility 需 Tasks 21–25 technical spike。
