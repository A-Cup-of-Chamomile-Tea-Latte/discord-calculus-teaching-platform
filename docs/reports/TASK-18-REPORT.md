# TASK-18 report — single-use activation-code domain logic

## Outcome

Complete。一次性「啟動碼」domain service、強隨機 provider、verifier-only storage、可選綁定、權限設定、生命週期、replay-safe 單次兌換、稽核、fixture 測試及 Sheets 1.1.0 schema migration 已完成；沒有部署、產生真人可用啟動碼或接觸真實 Google/Discord 資料。

## Summary

- 建立人工作業格式 `CALC-XXXX-XXXX-XXXX-XXXX`，以 32 字元 alphabet 的 16 個強隨機字元提供 80-bit 搜尋空間；輸入可忽略大小寫、空白與連字號。
- 正式 provider 只用 `crypto.getRandomValues`，不可用時拒絕發行，不以 UUID、時間戳或 `Math.random()` 降級；deterministic sequence provider 僅供 tests。
- Repository 只保存 SHA-256 verifier。Email/Discord 綁定及 idempotency key 也只保存用途分隔後的 fingerprints；明文只存在於建立結果。
- 新發行資料明列 role、course、class 與 permission allowlist；執行期驗證 actor ID、角色、權限、TTL、綁定格式及 idempotency key。
- 完成建立、到期、兌換、撤銷與所有結果稽核；成功兌換只回傳該筆 permission profile。
- 兌換在 `ActivationLock` 內執行；同 request hash 重送為 `REPLAY`，不同第二次嘗試為 `USED`，都不再次授權。
- GAS provider 使用 script-wide `LockService` global lock；文件明列吞吐量與 Google Sheets 無跨表 transaction 的限制，不宣稱 production-grade concurrency。
- ActivationCode contract 以 v1 optional extension 新增 binding、permission profile 與 request hash，維持原 1.0 records 可驗證；新 issuer 一律輸出完整欄位，授權端不得對 legacy 缺漏資料猜測權限。
- Sheets schema 升到 1.1.0 / migration `0002-activation-binding-permissions`，ActivationCodes seed 與資料字典同步更新。

## Files changed

- `apps/gas/src/activation/contracts.ts`：domain types、repository/random/hash/lock/audit ports 與 outcomes。
- `apps/gas/src/activation/service.ts`：發行、正規化、綁定、expiry、single-use redemption、replay、revocation、runtime validation 與 audit。
- `apps/gas/src/activation/in-memory.ts`：fixture repository、lock、audit sink 與 deterministic random source。
- `apps/gas/src/activation/runtime-providers.ts`：Web Crypto、Apps Script SHA-256 與 ScriptLock providers。
- `apps/gas/src/activation/service.test.ts`：36-test GAS suite 中的啟動碼 lifecycle、安全與 deterministic tests。
- `apps/gas/src/gas-globals.d.ts`：LockService 與 Utilities 最小型別。
- `apps/gas/src/sheets/schema.ts`、`apps/gas/fixtures/sheets-seed.json`、`apps/gas/docs/SHEETS_SCHEMA.md`：1.1.0 activation migration。
- `apps/gas/docs/ACTIVATION_CODES.md`、`apps/gas/README.md`：安全模型、生命週期、部署前提與併發限制。
- `contracts/schemas/activation-code.schema.json`、valid/invalid examples、`contracts/COMPATIBILITY.md`：相容的 v1 optional extension 與 plaintext rejection example。
- `fixtures/users/activation-codes.json`、`fixtures/users/README.md`、`fixtures/DATA_DICTIONARY.md`：四種 lifecycle、安全 fingerprints 與 permission fixtures。
- `docs/reports/TASK-18-REPORT.md`：本報告。

## Commands executed

- `npx prettier --write <Task 18 TypeScript/JSON/Markdown files>`。
- `npm run typecheck --workspace @calculus/gas`。
- `npm run test --workspace @calculus/gas`。
- `npm run build --workspace @calculus/gas`。
- `python -m pytest tests/contract -q`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `rg`、`wc` 與 `git diff --check` 作只讀 fingerprint/plaintext、migration、bundle 與 whitespace inspection。

沒有 publish/deploy、clasp login、Google Sheet write、Discord connection、network request、secret、真人啟動碼或外部 resource creation。

## Verification

- Tests：GAS Vitest 5 files / 36 tests、Portal Vitest 5 files / 25 tests、Pytest 35 tests全部 passed；其中 contract subset 32/32 passed。
- Linters/type checks：完整 root check 通過；secret scan 263 candidate files / 0 findings；Prettier、Ruff lint/format、GAS strict tsc、Astro check 41 files / 0 errors / 0 warnings / 0 hints、mypy 9 source files全部成功。
- Builds：GAS build 成功，`dist/Code.js` 32,898 bytes，manifest 同步輸出。
- Manual checks：GAS dist、GAS/根 fixtures 沒有 `plaintextCode`、fixture email、idempotency test key 或 deterministic demo code；root `activation-codes.json` 不含可兌換明文。

## Diagnostics

- `GasScriptLock` 是整個 script 的 global lock，不是 per-code row lock。它對低頻 prototype 提供同 deployment 內最強且簡單的互斥，但會序列化所有啟動碼兌換。
- Sheets 無跨 worksheet transaction；未來若 ActivationCodes 與 CourseMemberships 寫入分裂失敗，仍需狀態機、補償或對帳。
- Apps Script V8 的 Web Crypto 能力尚未在實際 deployment 驗證；目前 provider 會安全失敗，不會退回弱亂數。
- Activation domain 尚未掛入 `src/index.ts` 或公開 route，也沒有 Sheets repository；因此 production build 成功只驗證既有 GAS entrypoint，activation module 的可執行行為由 strict tsc 與 Vitest 驗證。
- Contract 為 schemaVersion 1.0 optional extension；這保留相容性，但正式 authorization 必須拒絕缺少 permission profile 的 legacy record，而非自動補權限。

## Assumptions made

- 啟動碼預設使用 80-bit entropy、5 分鐘至 7 天 TTL；實際課程的預設 TTL 留給 operator flow 決定。
- Role allowlist 為 `STUDENT`、`TA`、`INSTRUCTOR`、`OBSERVER`；permissions 為 join/access/ask/view 四項最小集合。
- Email 綁定採 trim + lowercase，Discord user ID 採 17–20 位數字字串；兩者都不保存明文。
- 相同 idempotency key 的第二次呼叫回 `REPLAY` 且 `ok=false`，表示已處理但不再次交付權限。
- Global lock 適合低頻人工發碼 prototype；不把它延伸解讀為高吞吐或跨 deployment 保證。

## Risks and blockers

- 高度：尚無 production `ActivationRepository`、route authentication、operator authorization 或 membership atomic workflow；不得公開啟用兌換 API。Mitigation：Task 19/後續 API 工作先定義認證與 write boundary，再接 Sheets adapter。
- 高度：跨表半成功可造成 code 已用但 membership 未建立。Mitigation：以 request hash + pending/committed state machine、可重試 upsert 與 reconciliation job 設計整合。
- 中度：需在目標 GAS V8 runtime 驗證 `crypto.getRandomValues`。Mitigation：deployment smoke test 必須先驗證 entropy provider，失敗則停止發行並改用經核准的 server runtime。
- 中度：SHA-256 binding fingerprint 對低熵 email/Discord ID 不能視為匿名化。Mitigation：限制存取與 retention；正式 threat model 可加入 deployment-held pepper，但不得把 pepper 寫入 repository。
- 無阻擋 Task 19 本機 fixture 工作的問題。

## Questions for ChatGPT discussion

- 正式兌換是由 GAS authenticated operator、Portal same-origin proxy，還是 Discord bot 執行？哪一層負責驗證使用者身分？
- ActivationCodes 與 CourseMemberships 應採何種 pending/commit/reconciliation 狀態機？
- 各角色的正式 permission matrix、預設 TTL、最大未使用量與 retention policy 為何？
- 是否需要 deployment-held HMAC pepper 取代單純 SHA-256 binding fingerprint？

## Recommended next action

執行 Task 19：建立帳號/啟動流程的 server-rendered pages 與安全 API adapter boundary，沿用本 Task 的啟動碼 domain contract，只用 fixture transport，不直接公開 GAS 或建立真實帳號。

## Copy-paste handoff

Task 18 已完成一次性「啟動碼」domain logic：格式為 CALC + 16 個不易混淆字元（80-bit），正式 provider 只用 Web Crypto 強亂數且不可用就安全失敗；repository 只存 verifier hash，email/Discord 綁定與 idempotency key 也只存 fingerprint，明文僅建立時回傳一次。已完成角色/權限 allowlist、建立/到期/單次兌換/撤銷/replay/audit，使用 GAS global ScriptLock；同 request 重送為 REPLAY、不同第二次為 USED。Contract 用 v1 optional extension 保留相容性，Sheets schema 升 1.1.0。完整檢查全過：GAS 36/36、Portal 25/25、Pytest 35/35、contract 32/32；secret scan 263 files/0 findings，Astro 41 files無問題，GAS build 32,898 bytes。尚未實作 production Sheets repository、公開 route、auth、operator UI 或跨表 transaction；global lock 不是 production-grade，且需在實際 GAS V8 驗證 Web Crypto。需決定兌換執行層、跨表 state machine、permission/TTL/retention 與是否使用 HMAC pepper。建議下一步 Task 19。
