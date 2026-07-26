# TASK-25 report — Private Support case boundary prototype

## Outcome

Complete。已完成 fixture-only Private Support boundary：Portal／bot modal creation、獨立 restricted representation port、owner 與 explicit teaching-team participants、escalation assignment、OPEN/ESCALATED/CLOSED status、30-day retention review hook、closure hook、無 public case number、analysis/content export deny policy及 metadata-only audit。沒有建立 production Discord channel/thread、沒有連線、沒有宣稱 Discord private permissions 已驗證。

## Summary

- PrivateSupportService 與一般 case/write service 分離，不接受 DiscordCourseWriter 或 DiscordThreadReader。
- CreatePrivateSupportCommand 明確標記 PORTAL 或 BOT 來源；兩者共用相同 owner、participants、retention、analysis exclusion 與 restricted provider policy。
- PrivateSupportCaseRecord 沒有 case-number 欄位或一般 Discord mapping；固定 visibility=TEACHING_STAFF、analysis_permission=EXCLUDED。
- Fixture 預設 RestrictedRepresentationKind.BACKEND_ONLY。PRIVATE_THREAD／RESTRICTED_CHANNEL 只作可替換 provider enum，fixture 即使選用也只回本機 reference，不建立 Discord resource。
- 建立時 participant set 是 owner 加明確 internal teaching-team allowlist；非 participant 無法讀取 record。
- Owner 或 allowlisted staff 可要求 escalation，但 assigned staff 必須在 teaching-team allowlist；status 轉為 ESCALATED，audit 只記 reason enum，不記敏感原文。
- Owner 或 allowlisted staff 可 close；restricted provider close、record CLOSED/closed_at 與 closure hook 都有 fixture trace。
- Retention review timestamp 由 timezone-aware clock 加 30 天計算；hook 代表待審查工作，不等同自動刪除或 legal hold 決策。
- PrivateSupportDataPolicy 對 public case number、analysis inclusion、content export 一律 deny；既有 audit-only export fixture仍可保留 0 message count 的非內容 manifest。
- PrivateSupportModal 使用兩個私密 interaction inputs（title 1–160、body 1–1800），只對已映射 internal actor 開啟；成功只回 ephemeral confirmation，不會建立 public lookup key。
- 現有 Portal fixture/GAS/client adapters 的 public lookup tests 已持續證明 PSUP/private case 回 NOT_FOUND；Case schema 也要求 PRIVATE_SUPPORT 的 caseNumber=null、visibility=TEACHING_STAFF、analysisPermission=EXCLUDED。
- PRIVATE_SUPPORT_SPIKE.md 提供隔離 test guild 的 permission／visibility／failure／cleanup 驗證計畫；通過前不切換 backend-only 預設。

## Files changed

- bots/course_assistant/private_support.py：case／participant／representation／audit models，repository/provider/audit/lifecycle ports，in-memory fixtures，data deny policy，以及 create/escalate/close service。
- bots/course_assistant/private_support_interaction.py：Private Support button/view、Discord modal 與 identity-safe ephemeral adapter。
- bots/course_assistant/PRIVATE_SUPPORT_SPIKE.md：private thread、restricted channel、backend-only 比較與 live technical-spike checklist。
- bots/course_assistant/README.md：Task 25 責任、default representation、data exclusion 與 spike 邊界。
- tests/bots/test_private_support.py：8 個案例，涵蓋 Portal/Bot creation、participants、escalation、closure、retention、public lookup、analysis/export deny 與無 public writer/reader dependency。
- docs/reports/TASK-25-REPORT.md：本報告。

既有 contracts 與 Portal public adapters 已符合 acceptance，因此未改 schema 或 UI；完整回歸測試證明其排除規則仍有效。

## Commands executed

- sed/rg 查閱 Task 25、ADR-0010、Tasks 23–24 reports、case/export contracts、private invalid examples、Portal lookup/form adapters/tests、fixtures 與 bot hooks。
- ruff format／ruff check Task 25 Python files。
- strict mypy Task 25 course-assistant modules/tests。
- pytest -q tests/bots/test_private_support.py tests/bots/test_anonymous_reply.py tests/bots/test_course_assistant.py。
- npx prettier --write Task 25 Markdown files。
- npm run check。
- npm run build。
- git diff --check 與 rg no-writer/no-reader/no-public-lookup invariants。

沒有 Discord token/login、Gateway/REST call、OAuth、channel/thread/role creation、permission overwrite、public message、email、cloud resource、real data、deploy 或 push。

## Verification

- Tests：Task 25 8/8 passed；Task 25 + anonymous reply + Course Assistant 定向 25/25 passed；完整 Pytest 86/86、Portal Vitest 25/25、GAS Vitest 44/44 passed。
- Linters/type checks：root check 通過；打包前最後 secret scan 321 candidate files / 0 findings；Ruff format/lint 通過；strict mypy 46 source files 無問題；GAS tsc 通過；Astro check 41 files / 0 errors / 0 warnings / 0 hints。
- Builds：Portal static build 14 pages；GAS bundle 成功產生 dist/Code.js 與 dist/appsscript.json。
- Manual checks：Private Support source 無 DiscordCourseWriter、DiscordThreadReader、create_case_thread；public lookup fixture serialized data 無 private case ID/PRIVATE_SUPPORT；private audit 無 body；record 無 case_number；data policy 三項 deny；provider calls全為 in-memory fixture。
- Known warnings：Python 3.14 下既有 discord.py 2.7.1 /health test 仍有 2 個 asyncio.iscoroutinefunction deprecation warnings；Task 25 沒有新增 warning。

## Diagnostics

- Discord 的 channel/thread visibility 取決於 permission overwrites、角色階層、parent inheritance、client behavior 與 resource lifecycle；只靠本機模型不能證明 production privacy。正式 spike 必須使用隔離 test guild，逐一驗證 owner、assigned TA、未指派 TA、一般學生、archive reader 與離開 guild 的帳號。官方權限背景：[Discord permissions](https://docs.discord.com/developers/topics/permissions)。
- 現有 Case contract 已正確把 Private Support 的 case number、visibility、analysis permission綁成條件式規則；Task 25 service另以不同 record type避免一般 case adapter誤用。
- ExportManifest schema允許 PRIVATE_SUPPORT + EXCLUDED；fixture是 messageCount=0 的 audit-only manifest。Task 25 data policy禁止內容 export/analysis，但未禁止最小 audit manifest；Task 26需把此差異寫成明確 pipeline rule。
- Restricted provider目前把敏感 title/body只存於 in-memory provider call，private audit永不存原文。正式 backend需要 encryption/access logging/retention/backup policy。
- Teaching-team participant set目前是明確 internal user allowlist，不使用 broad Discord role作資料庫。正式 roster變更需撤銷存取與重新驗證representation ACL。
- Provider create、repository insert、retention hook、audit append、idempotency complete不是單一 transaction；任何中途故障都需 durable outbox/reconciliation，不能 fallback public或blind retry。

## Assumptions made

- Prototype default採 BACKEND_ONLY，直到 technical spike與隱私審查核准其他機制；PRIVATE_THREAD/RESTRICTED_CHANNEL enum不代表安全認證。
- 建立者永遠是 owner；建立時明確 teaching-team allowlist成員成為 participants。Escalation不是首次授權整個team，而是指定負責staff並改變狀態。
- Owner與allowlisted staff都可close；closure hook只通知後續流程，不立即刪除資料。
- Retention 30天是 fixture值，只代表 review date；正式天數、legal hold、恢復期限及刪除方式待 Task 29。
- Public lookup對 Private Support一律以 NOT_FOUND處理，不確認存在性；沒有可供使用者公開查詢的 case number。
- Audit-only、0-message、EXCLUDED manifest可供受限營運稽核；任何內容/anonymization/teaching analysis export預設禁止。

## Risks and blockers

- 高：正式 private Discord mechanism未驗證。Mitigation：依 PRIVATE_SUPPORT_SPIKE.md 在隔離 guild測試並由privacy owner核可；之前保持 backend-only。
- 高：正式 backend identity/ACL/encryption/backup/retention/audit尚未完成。Mitigation：Task 29 threat model + Task 32 integration/auth/storage design。
- 高：多步 side effects有 partial failure。Mitigation：durable idempotency/outbox/reconciliation，禁止公開 fallback與盲重送。
- 中：Teaching-team roster變更後participant access撤銷未實作。Mitigation：正式 repository加membership version與reconciliation。
- 中：Retention hook沒有purge/legal-hold engine。Mitigation：Task 29定政策，Task 32定執行與可恢復刪除。
- 無阻擋 Task 26 local export pipeline 的問題，但 Private Support content必須保持排除。

## Questions for ChatGPT discussion

- Private Support 應永久採 backend-only，還是有足夠理由承擔 Discord private representation 的可見性與營運風險？
- 建立時全體 allowlisted teaching team可存取是否過寬；應否只給 triage group，再經 escalation加入 assigned staff？
- Closure後的 retention review、legal hold、可恢復刪除與最終 purge由誰核准與執行？
- Audit-only manifest需要哪些最小欄位，才能支援營運稽核又不建立敏感 existence side channel？

## Recommended next action

依使用者指示在 Task 25 後暫停，不開始 Task 26。新環境恢復時，先讀 handoff 文件與 Batch D summary，重新安裝依賴並跑 npm run check；確認 archive hash後再從 Task 26 local export pipeline繼續。

## Copy-paste handoff

Task 25已完成 Private Support fixture boundary：Portal/Bot modal兩種create來源、獨立PrivateSupportService、owner+explicit teaching-team participants、allowlisted staff escalation、OPEN/ESCALATED/CLOSED status、30日retention review hook、closure hook、metadata-only audit，以及可替換restricted representation port。預設只啟用BACKEND_ONLY；PRIVATE_THREAD/RESTRICTED_CHANNEL只是enum與fixture port，沒有建立Discord資源或宣稱權限安全。Private record沒有public case number或一般Discord mapping，固定TEACHING_STAFF + EXCLUDED；public lookup、analysis、content export三項policy全部deny，audit-only 0-message manifest例外留待Task 26明確化。Task 25 8/8、完整Pytest 86/86、Portal 25/25、GAS 44/44全過；secret scan 321/0、mypy 46 files、Astro 41 files零診斷；Portal 14 pages與GAS bundle build成功。已寫PRIVATE_SUPPORT_SPIKE.md，要求在隔離test guild驗證owner/TA/student/archive-reader可見性、permission inheritance、restart/archive/close/failure/cleanup，通過前維持backend-only。正式identity/ACL/encryption/retention/outbox仍mocked。依使用者指示Task 25後打包暫停；新環境從Task 26繼續。
