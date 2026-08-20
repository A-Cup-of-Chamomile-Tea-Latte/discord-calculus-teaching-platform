# Ordered next steps

## 已壓縮完成

本機 implementation、compact Sheet、雙向 Google Bridge smoke、安全 synthetic cleanup、SQLite
live-copy backup／restore／migration rehearsal 均已完成。不要重跑 44-action Sheet migration、另建 OAuth
client、另寫一份 Phase 2C 報告，或把 corpus／LLM 分析拉進本階段。

Mac `course_assistant` 與 `dump_bot` 仍是唯一 live writers；status digest 未啟用。

## 1. 需要人工開網頁或提供／核對外部資訊

依序完成：

1. **Google OAuth 長期模式**：在 Google Auth Platform 將 External app 切到 Production，並處理
   Google 要求的驗證；或明確接受 Testing 模式約每 7 天重新授權。必要時只使用 Chrome
   「Ding Ding」重新授權一次。
2. **Remote host identity**：提供 SSH username、Tailscale hostname／private IP、預期 host-key
   fingerprint。不要在聊天傳 password、private key、Discord token 或 OAuth credential。
3. **Remote staging**：Codex 取得 host identity 後，執行唯讀 audit、staging install、remote
   synthetic smoke、backup／restore rehearsal 與 one-writer readiness。Mac bots保持運作。
4. **Live cutover approval**：所有 remote receipts PASS 後，使用者輸入精確
   `GO-LIVE-CUTOVER`。在此之前不得停 Mac writer 或啟動 remote production writer。
5. **Bound digest**：remote heartbeat 穩定後才安裝 trigger；若 Google 要求，人工在 Ding Ding
   完成授權。

## 2. 必須等待 24 小時

Cutover 成功後才開始計時。期間驗證單一 writer、三個 remote services、Discord connectivity、
queue depth、OAuth refresh、GAS heartbeat、backup 與 compact Sheet projection。滿 24 小時後原地更新
Phase 2C report，再決定是否進入小規模試用。

## 固定停止線

- SQLite 是 authority；任何 cloud fetch 都必須驗 version、checksum、source 與 operator confirmation。
- 不把 raw messages、姓名、學號、Discord ID、Email、附件、Private Support、credential 放進
  chat、Git、公開 ZIP 或 LLM。
- 不建立 public SSH、public GAS endpoint、第二個 production writer，或未經核准的 email／分析流程。
