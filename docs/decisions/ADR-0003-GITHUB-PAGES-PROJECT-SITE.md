# ADR-0003: 使用 GitHub Pages project site

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: Repository 維護者
- Related tasks: 14, 30, 33

## Context

既有 owner site repository 已有用途，不應被新原型取代。新入口網站若未來獲授權發布，需位於另一個 repository 的 project site，URL 會包含 repository base path。

## Decision

Astro build 預留可設定 project-site base path。未獲明確授權前，只建本機設定與 CI build，不建立 remote、不啟用 Pages、不部署。

## Consequences

### Positive

保留既有 owner site，靜態原型可獨立回復與停用。

### Negative

資產與內部連結必須正確處理 base path；GitHub Pages 本身不提供私密後端。

### Operational

repository 名稱、owner 與 base path 都視為部署前需再次確認的設定。任何 Pages workflow 都需要另行授權。

## Alternatives considered

取代 owner site 會破壞既有用途；自架 server 增加營運責任；其他靜態 host 可行但目前沒有選用理由。

## Reversal strategy

使用相對／base-aware URL，不把 GitHub domain 寫死。未來可將同一份 static output 移至其他 host，或改用自訂網域。

## Open questions

建議名稱 `discord-calculus-teaching-platform`、實際 owner 與公開時程均未獲部署確認。
