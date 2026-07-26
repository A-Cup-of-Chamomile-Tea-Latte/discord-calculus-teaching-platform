# TASK-29 report — security, privacy, and abuse review

## Outcome

Complete。已完成 fixture-first 實作的安全、隱私與濫用審查，建立 20 項有具體 component/file 證據的 findings（15 高、5 中）、data classification/trust boundaries、production blockers、學生版隱私／陌生 DM 指南草稿，以及 incident/safe-fallback runbook。每個高風險都有 owner 與 next action；本文明確不宣稱法律合規或 production readiness。

## Summary

- 審查覆蓋 server nickname 與 Discord global profile、unsolicited DMs、public case-number enumeration、anonymous-author traceability、activation-code share/replay、email/contact PII、bot token separation/least privilege、GAS execute-as-owner、Sheets access、Portal/GAS CORS/CSRF、Private Support、raw/sanitized exports、consent/AI handoff、fixtures/secrets/archives in Git、spam/rate limit、incident/fallback，並補充 mention/UI injection、voice prohibition、mock-evidence 與 multi-step partial failure。
- Findings 狀態使用「已修復／已緩解／原型接受／未解」，另區分 fixture prototype 當下暴露與 production blocker，避免把無網路 mock tests 誤當真實服務證據。
- 最主要的上線 blockers 是 public-case access scope/rate limit、GAS owner authority 與 authenticated same-origin transport、Private Support 正式 ACL、Sheets access/retention、live bot permission/token isolation、email/activation auth+abuse control、raw export/consent snapshot/withdrawal/release gate，以及 incident owners/kill switches。
- 特別診斷 repository 中 `project-exchange/*.zip` 不會被現有文字 secret scanner 解壓深度掃描；首次 commit/remote 前必須排除或離線解壓逐檔掃描，不能用 `0 findings` 推論 archive 安全。
- 學生指南明確 `nnmmm` 不隱藏全域 profile、建議關閉 shared-server unsolicited DM、不交出 token/code、如何處理可疑 DM、一般匿名不等於 Private Support、管理者可受限追溯、同意與撤回語意，並留有發布前 TBD 正式聯絡欄位。
- Runbook 提供 SEV-1/2/3、前 30 分鐘動作、component fallback matrix、證據最小化、復原準則，強制 Private Support 無 public fallback、單 bot token 獨立 revoke、export/AI mis-send 立即停止與追蹤 destination。
- 已與 Task 32 `PRODUCTION_INTEGRATION_PLAN.md` 的 Gates 0–7 對齊；Task 30 CI 與 Task 32 fixture journey 通過仍不被視為 live security evidence。

## Files changed

- `docs/security/SECURITY-PRIVACY-THREAT-MODEL.md`：資產／資料分級、信任邊界、20 findings、owners/next actions、9 項 production release gates、原型安全底線與限制。
- `docs/security/USER-PRIVACY-DM-GUIDE-DRAFT.md`：可供學生閱讀的繁中隱私、DM、匿名、Private Support、consent 與帳號事件指南草稿。
- `docs/security/INCIDENT-AND-SAFE-FALLBACK-RUNBOOK.md`：事件角色／分級、containment、降級矩陣、evidence/recovery 與 prototype emergency stop。
- `docs/decisions/UNRESOLVED.md`：新增 U-012–U-015，記錄 GAS owner/CORS transport、資料 retention/deletion/backup、consent snapshot/withdrawal/AI release、Git archive deep scan 未決項。
- `docs/reports/TASK-29-REPORT.md`：本完成報告。

## Commands executed

- 以 `sed`、`rg`、`find` 完整閱讀 Task 29/shared context/defaults/report template、Tasks 26–28/30/32 報告、所有 ADR、Portal/GAS/bot/export/anonymizer 實作與運作文件。
- `npx prettier --write docs/security/*.md docs/decisions/UNRESOLVED.md`。
- `npx prettier --check docs/security/*.md docs/decisions/UNRESOLVED.md`。
- `rg` 檢查 finding 數量、主題覆蓋、owner/next action、production blocker、不宣稱法遵／production-ready 與未決項登記。

沒有連線 Discord/Google/email/AI，沒有使用真實資料或 secret，沒有寄信、建立雲端資源、deploy、commit 或 push。

## Verification

- Tests：Task 29 只改 Markdown，無 runtime test 增減。根據已完成的 Task 30 整合 baseline，Python 113/113、Portal 25/25、GAS 44/44 通過；Task 32 fixture journey 1/1 也已通過。Task 29 完成後的 full repository suite 交由 Task 33 統一重跑與記錄，本 task 不重複執行。
- Linters/type checks：Task 29 相關 4 個 Markdown files 的 Prettier check 通過；結構檢查確認 F-01–F-20 連續、15 高／5 中、每項有狀態且每項高風險有 owner/next action。
- Builds：本 task 無 application code 變更，未單獨重跑 build；Task 30 baseline 的 Portal 14 pages 與 GAS bundle 成功，最終將由 Task 33 統一重跑。
- Manual checks：Task 29 規格列出的 16 個必要主題全部出現在 findings，原型風險與 production blocker 分開，使用者指南與 incident/fallback instructions 均已納入。

## Diagnostics

- `apps/gas/appsscript.json` 目前 `access=MYSELF` 是 fail-closed，但 `executeAs=USER_DEPLOYING` 意味著未來放寬 access 會讓 public caller 借用 owner Sheet/Mail authority；不能用 CORS 當 authorization。
- Public case number 現為可讀六位流水號，GAS fixture 還有 list route，而 GitHub Pages 是 internet-public；真實資料前必須完成 Task 33 U-011 與 Gate 6 access-scope 決策。
- `project-exchange/*.zip` 是現有 secret scan 的 binary/archive blind spot。這是首次 commit/remote 前 blocker，不表示已在 archive 中發現 secret。
- Raw Task 26 export 刻意保留 internal/Discord IDs 與 EXCLUDED content，Task 27 只能降低風險、不能證明不可逆匿名；consent version/snapshot/withdrawal 與附件複核仍是 release blocker。
- Export integrity 目前已有兩層綁定：anonymizer 驗證 raw manifest 每個 file SHA-256，sanitized package 寫入 source export ID/thread hash，importer 會拒絕 metadata/sanitized mixed package。Residual：import dry-run stdout 包含完整 sanitized body，operator 不得把輸出寫進共用 CI/log/chat。
- Private Support 只有 `BACKEND_ONLY` fixture 是保守預設，不表示 backend 已有 production ACL/encryption/backup/retention；Discord private representation 也尚未在隔離 guild 驗證。

## Assumptions made

- 審查以 2026-07-19 當前 repository 為準，且所有原型將繼續 fixture-only，直到 Task 33 與後續核准。
- GitHub Pages 是 internet-public；「全課程可見」不自動等於允許全網存取。
- 學生 DM 指南使用功能描述而不鎖定 Discord 當下 UI 文字；發布前需用當時 client 再核對。
- Retention 天數、正式 incident contact、雙人 release approval 與法遵通報不在本 task 自行宣告；它們保留為需要教學／隱私／組織 owner 核准的治理決策。

## Risks and blockers

- 高：Public case lookup 的 course-only vs internet-public access scope、list-all route、rate limit 與公開欄位未決。Mitigation：Gate 6 + Task 33 決策前只用 fixtures，不發布可識別案件。
- 高：GAS/Sheets/email/activation 尚無 production auth、ACL、CSRF、outbox、rate limit、retention 與 incident kill switch。Mitigation：保持 `access=MYSELF`/mock/future adapter fail closed，依 production Gates 4–6 逐關驗證。
- 高：Private Support 正式 mechanism/ACL 與 anonymous trace audit 未核准。Mitigation：維持 BACKEND_ONLY fixture、內容 export deny、無 public fallback，Gate 3 完成可見性矩陣才開放。
- 高：Raw exports、consent withdrawal 與 AI destination governance 未完成。Mitigation：不外傳 raw，只使用人工核准 sanitized package，Gate 0/7 前不連 AI。
- 高：交接 ZIP 無 deep scan。Mitigation：首次 commit 前排除或離線解壓掃描，經 repository/security owner 核准才 stage。

## Questions for ChatGPT discussion

- 正式 public lookup 應採 course session、case PIN、signed link，或取消 GitHub Pages 的 dynamic case access？Production 是否完全移除 list-all route？
- Private Support 是否永久 backend-only；追溯匿名作者的 allowlist、break-glass owner 與 audit retention 如何核准？
- Raw export、sanitized package、consent snapshot、email/contact、audit 與 Private Support 各自保留多久；撤回後是否重處理/刪除已產生 package 與 recipient copy？
- 分析 release 是否要求雙人複核，並保存無原文的 approval/destination/deletion audit？
- `project-exchange` 交接 archives 應完全排除於 remote，或可在解壓深度掃描、inventory/hash 後納入？

## Recommended next action

執行 Task 33 最終診斷與 go/no-go review：整合 Tasks 29–32，重跑 full check/build，將本威脅模型的 production blockers 對齊 U-011–U-015 與 `PRODUCTION_INTEGRATION_PLAN.md` Gates 0–7，明確保持 no-deploy/no-real-data 狀態。

## Copy-paste handoff

Task 29 已完成繁中安全／隱私／濫用審查，新增威脅模型、學生 Discord 隱私/DM 指南草稿與 incident/safe-fallback runbook。共 20 findings（15 高、5 中），每項有 concrete file/component、已修復/已緩解/原型接受/未解狀態；每項高風險都有 owner 與 next action，並明確區分 fixture prototype 與 production blockers。關鍵 blockers：public case 可枚舉且 Pages 全網公開、GAS execute-as-owner/CORS/auth、Sheets/Private Support ACL/retention、live bot least privilege、email/activation abuse control、raw export/consent snapshot/withdrawal/AI release、rate limit/kill switches。現有 secret scanner 不解壓 `project-exchange/*.zip`，已列為首次 commit 前 blocker。UNRESOLVED 新增 U-012–U-015。Task29 文件 Prettier 通過；目前 Task30 baseline 為 Python 113/113、Portal 25/25、GAS 44/44，Task32 fixture journey 1/1；Task33 將整合後重跑 full check/build。沒有使用真實資料/secret、沒有連 Discord/Google/email/AI、沒有部署或外部動作，不宣稱法律合規或 production-ready。建議下一步直接 Task 33 最終診斷，保持 no-deploy/no-real-data。
