# TASK-13 report — onboarding, question submission, and support forms

## Outcome

Complete。加入／設定、一般問題與 Private Support 三條 route 都有 fixture-only form、清楚 validation 與同頁 confirmation；沒有網路傳輸、檔案上傳或 browser persistence。

## Summary

- `/join/` 提供 Discord connection placeholder、NTU email、選填 Gmail、01/02 班別、`nnmmm` fixture alias 預覽、規則／隱私確認、教學分析預設與 DM privacy 建議。
- `/ask/` 提供標題、內容、三種 visibility、三種作者顯示、analysis permission、附件 metadata placeholder 與 NTU COOL authoritative acknowledgement。
- `/private-support/` 保持獨立 route 與醒目警告；固定只限授權教學團隊、不產生 public case number、analysis `EXCLUDED`。
- 三個表單都以 non-punitive error summary 保留輸入、標記 `aria-invalid`，成功後顯示本機 confirmation 與明確的「未送出／未建立帳號或案件」說明。
- 匿名一般問題明確說明 follow-up 必須由網站或 Discord modal 轉交 bot 代貼。
- confirmation 使用 `textContent` 建構摘要，不使用 HTML injection；reset 會清除表單並回到第一個控制項。

## Files changed

- `apps/portal/src/lib/fixture-form-prototypes.ts`：三種表單的純 validation、`nnmmm` 預覽與 confirmation projection。
- `apps/portal/src/lib/fixture-form-prototypes.test.ts`：email domain、alias、一般匿名問題、Private Support exclusion 與 no-storage/no-network tests。
- `apps/portal/src/scripts/fixture-forms.ts`：表單初始化、accessible errors、confirmation rendering、reset 與 alias preview。
- `apps/portal/src/pages/join/index.astro`：完整 fixture onboarding form。
- `apps/portal/src/pages/ask/index.astro`：一般問題 form 與 general/private route 對照。
- `apps/portal/src/pages/private-support/index.astro`：獨立 Private Support form、固定隱私設定與 confirmation。
- `apps/portal/src/styles/global.css`：choice groups、error summary、prototype panel、confirmation、mobile definition-list layout。
- `docs/reports/TASK-13-REPORT.md`：本任務交接報告。

## Commands executed

- `npx prettier --write <Task 13 Astro/TypeScript/CSS files>`
- `npm run check --workspace @calculus/portal`
- `npm run test --workspace @calculus/portal`
- `ASTRO_BASE_PATH=/portal-test npm run build --workspace @calculus/portal`
- `npm run verify:dist --workspace @calculus/portal -- /portal-test/`
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`
- `rg` static dist scan for storage/network APIs and fixture confirmation markers。

沒有寄信、連 Discord、上傳檔案、建立 remote resource、deploy、publish 或使用 secret。

## Verification

- Tests：Vitest 4 files、17 tests passed；Task 13 新增 5 個 form tests。Pytest 35 tests passed。
- Linters/type checks：完整 root check 通過；secret scan 221 files / 0 findings；Prettier、Ruff lint/format、GAS TypeScript、mypy（9 source files）均通過；Astro check 38 files，0 errors、0 warnings、0 hints。
- Builds：`/portal-test/` static build 成功產生 14 pages；dist verifier 通過 10 required pages、131 base-safe links。
- Manual checks：三種 confirmation markers 均存在 client bundle；dist 掃描沒有 `localStorage`、`sessionStorage`、IndexedDB、cookie、fetch/XHR、beacon 或 WebSocket；三條 route 的一般／Private 差異、warning 與 reset 文案皆逐頁檢查。

## Diagnostics

- Validation 與 confirmation projection 是純函式，後續若接 GAS 可保留 UI contract，另加 server-side validation；不得只信任 client validation。
- Fixture reference 是固定、明確標示不具正式效力的字串，不可拿來 public lookup。
- Attachment 欄位只接受使用者自行輸入的 filename/size 描述，不建立 `<input type="file">`，因此不會讀取檔案。
- confirmation 會在目前 DOM 顯示 email/title 等摘要；按 reset 或重新整理可清除，但共享裝置使用者仍應避免輸入真實敏感資料到此 prototype。

## Assumptions made

- NTU email prototype 以 `@ntu.edu.tw` 作為可逆的格式規則；正式身分驗證仍由 Task 19 與課程 membership policy 決定。
- `nnmmm` 預覽固定使用 joining order `042`，只示範 `classCode + 3 digits`，不代表正式排序或指派。
- 一般問題預設 `CLASS`、`COURSE_ALIAS`、`INCLUDED`；使用者可在送出 fixture 前改選。
- Private Support 在 UI 固定 `EXCLUDED`，不提供 opt-in；這遵循既有 contract 與 privacy default。

## Risks and blockers

- 高度：正式連線後所有 validation 與 privacy constraints 必須在 GAS/bot backend 再驗證，不能信任 client payload。
- 高度：Private Support 尚無受保護 backend、授權模型或 retention policy；目前只可當 UX prototype。
- 中度：`@ntu.edu.tw` 未必涵蓋正式允許的所有校方 alias/domain；Task 19 應確認 allowlist。
- 中度：真實 attachment upload 尚未設計 malware scan、size/type limit 與 retention；目前刻意不提供 upload。
- 無阻擋 Task 14 的問題。

## Questions for ChatGPT discussion

- 正式 NTU email allowlist 是否只接受 `@ntu.edu.tw`，或需要其他校方子網域？
- `nnmmm` joining order 應依 verified membership、核發順序，還是匯入名單固定指派？
- 一般問題選 `TEACHING_STAFF` 時，是否仍屬一般案件並可取得 public case number？
- Private Support 正式 retention 與可存取角色應如何定義？

## Recommended next action

執行 Task 14：加入 GitHub Pages project-site workflow、base-path build/verification 與部署前文件；只建立本機 workflow 檔，不 push、不啟用 Pages、不建立 remote resource。

## Copy-paste handoff

Task 13 已完成：`/join/`、`/ask/`、`/private-support/` 都有 fixture-only forms 與同頁 confirmation。Join 包含 Discord placeholder、NTU email、選填 Gmail、班別、`nnmmm` 預覽、規則/隱私、analysis default 與 DM 建議；一般問題包含標題/內容、visibility、姓名/alias/匿名、analysis、attachment metadata 與 NTU COOL 確認；Private Support 獨立、不公開查詢、不產生 public case number且預設排除分析。Validation 保留輸入並提供 accessible error summary；匿名 follow-up 明確要求網站/modal 由 bot 代貼。完整 root check 通過：Vitest 17/17、Pytest 35/35、secret scan 221 files/0 findings、Prettier/Ruff/mypy/TypeScript/Astro 均成功；`/portal-test/` build 14 pages、dist verifier 10 pages/131 links 通過，產物沒有 browser storage、cookie 或網路傳輸 API。正式 email/Discord/GAS/file upload/private backend 都仍為 mock。需決定 email allowlist、alias 指派規則與 Private Support retention/roles。建議下一步 Task 14 GitHub Pages project-site workflow（只寫本機檔案，不部署）。
