# Ordered next steps

更新日期：2026-08-24

## 已完成 checkpoint：Portal 架構改版

- 2026-08-24 已完成首頁、加入、案件查詢、合併指南、Footer 與管理員 status 的架構改版與 QA。
- Public artifact 只剩 5 個允許頁面；無內部登入、舊路由、reviewer 文案或 fixture Discord 連結。
- 未接線的加入與案件查詢在 public build fail closed；fixture 操作只留 reviewer build。
- 舊 Portal 資料位於可逆 archive stage，不再與現行設計並列。
- 已完成手機／iPad 橫式瀏覽器檢查與 10 頁 A4 landscape 列印驗收。

## 1. 完成 production observation 與 source reconciliation

1. 2026-08-24 17:12 後取得新的 owner-only `/ops status` 安全摘要。
2. 確認三服務健康、heartbeat 新鮮、remote 是唯一 writer、queue 排空、manual attention 為 0。
3. PASS 後依檔案 ownership 將 v6 runtime／migration／tests 安全吸收回 canonical repository；不得覆寫 Portal 與 115-1 進行中變更。

## 2. Portal 動態能力

### 加入申請

- same-origin backend、CSRF／rate limit、SQLite state machine。
- Course Manager 兩級審核權限。
- Discord 成員比對、學生／訪客角色、暱稱與 Discord DM。
- duplicate／waiting／approved／rejected／archived 的冪等與稽核。

### 案件查詢

- 接受一般與 `-P` 完整案號。
- 只回傳案號、類型、狀態、更新時間、是否有教學團隊回覆與 Discord 連結。
- 不回傳題目、對話、作者、附件、AI、內部 ID；不提供 list-all 或背景 polling。

## 3. Discord 隱密支援

現有 production `/private open` 必須依最新 UX checklist 完成 production 化或暫時隱藏。公開／隱密共用案件設定，差別只在 visibility；Portal 不收內容或附件。初始限制為每人 2 分鐘 1 次、每小時 5 次、24 小時 20 次，超量時保留 queue。

## 4. 教學上線準備

- Owner 使用教師白帳號走一次 Discord 新手流程後，再補圖解簡報。
- 完成資料告知、保留／刪除、Private ACL regression、事故責任與 rollback。
- Repository、網址、backend origin 與首次 deploy 仍需明示核准。

## 固定停止線

- 不以 Portal 工作覆寫尚未吸收的 production v6 runtime。
- 不把 raw messages、學生姓名／ID、Email、Discord ID、附件、Private Support、SQLite rows、credential 或 secrets 放進 Git、聊天或公開 artifact。
- SQLite 是 operational authority；Browser 永不持有 Bot token、Google owner credential 或 SQLite write access。
- 未完成 auth、rate limit 與 storage gate 前，不開啟公開動態 submission／lookup。
