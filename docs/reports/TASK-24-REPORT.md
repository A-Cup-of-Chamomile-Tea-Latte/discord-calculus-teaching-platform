# TASK-24 report — anonymous modal reply prototype

## Outcome

Complete。已完成 fixture-first Discord anonymous reply prototype：案件綁定 button、私密 modal、owner authorization、1–1800 字驗證、course-alias／fully-anonymous 顯示分流、bot repost、mention suppression、ephemeral submitter acknowledgement、anti-duplicate idempotency 與 metadata-only private audit。沒有接收後刪除一般訊息、沒有連 Discord、沒有 command sync 或 guild write。

## Summary

- AnonymousReplyView 提供綁定 case ID 的 button；callback 只呼叫 anonymous-reply adapter，不監聽一般 message。
- AnonymousReplyModal 使用 discord.py 2.7 Label + paragraph TextInput，required、min 1、max 1800、timeout 300 秒；內容在 interaction submit 前不出現在公開頻道。
- AnonymousReplyDiscordAdapter.open_modal() 先將 Discord user ID 經 injected identity resolver 換成 internal ActorContext，再驗證案件擁有者；找不到身分或未授權時只回 generic ephemeral failure。
- Modal submit 會再次解析 actor 並重新授權，operation ID 由 Discord interaction ID 衍生；成功回覆永遠是 ephemeral。
- CourseAssistantService.authorize_anonymous_reply() 要求 reply-enabled policy、owner internal user ID 完全相符、case-thread mapping 存在，並驗證顯示政策。
- COURSE_ALIAS 必須帶五位數 nnmmm label；ANONYMOUS 必須完全沒有 alias，公開 label 固定為「匿名同學」。兩者不混用。
- Public writer body 只由安全 label + modal body 組成，不插入 actor internal ID、Discord ID、username 或 nickname；writer call 明確 suppress_mentions=True。
- AnonymousReplyAuditRecord 私下保留 operation ID、case ID、internal actor user ID、public message ID、display mode、occurred time，沒有 raw body 或 Discord public identity。
- Idempotency replay 會驗證已完成 operation 與 audit record 一致，回傳 duplicate result 而不再次寫 Discord。
- Fixture interaction test 分開模擬「開 modal」與「submit modal」兩個 interaction：開啟階段無 public writer call，送出後只有一個 bot send_message call，submitter 只收到 ephemeral confirmation。

## Files changed

- bots/course_assistant/models.py：anonymous display mode、case policy、command、private audit record 與 publish result。
- bots/course_assistant/repositories.py：anonymous case policy/audit ports 與 fail-closed in-memory fixtures。
- bots/course_assistant/service.py：owner authorization、內容驗證、安全 label、idempotent repost 與 private audit。
- bots/course_assistant/anonymous_reply.py：discord.py modal、button/view、identity resolver 與 generic ephemeral interaction adapter。
- bots/course_assistant/README.md：新增 Task 24 interaction、privacy、display-mode 與 audit 邊界說明。
- bots/common/ports.py：writer send_message 新增 deny-by-default mention-suppression capability。
- bots/common/testing.py：fixture write trace 記錄 mentions_suppressed。
- tests/bots/test_anonymous_reply.py：8 個案例，覆蓋完整匿名、課程代號、非 owner、空白／過長、modal controls、ephemeral flow、button binding 與 no-delete invariant。
- docs/decisions/UNRESOLVED.md：新增 U-010，記錄 anonymous reply private audit 的正式 contract 尚待 Task 29/32 決定。
- docs/reports/TASK-24-REPORT.md：本報告。

## Commands executed

- sed/rg 查閱 Task 24、shared context、Task 22 report、bot interfaces、hooks/service/repositories、consent/audit/CaseMessage contracts、fixtures 與 discord.py 2.7 Modal/TextInput/Label 實作。
- ruff format bots/common bots/course_assistant tests/bots。
- ruff check bots/common bots/course_assistant tests/bots。
- mypy bots/common bots/course_assistant 與定向 tests。
- pytest -q tests/bots/test_anonymous_reply.py tests/bots/test_course_assistant.py tests/bots/test_common_fakes.py。
- npm run check。
- npm run build。
- npx prettier --write Task 24 Markdown files。
- git diff --check 與 rg privacy/ownership/no-delete/no-reader-leak invariant 檢查。

沒有 token、Discord login、Gateway/REST call、command sync、normal-message event、message deletion、真實 modal submission、guild/channel/thread/message write、remote resource 或部署。

## Verification

- Tests：Task 24 定向 8/8 cases passed；Task 24 + Course Assistant + common fake 定向共 20/20 passed；完整 Portal Vitest 25/25、GAS Vitest 44/44、Pytest 78/78 passed。
- Linters/type checks：完整 root check 通過；報告加入後最後 secret scan 313 candidate files / 0 findings；Prettier、Ruff lint/format 通過；strict mypy 43 source files 無問題；GAS tsc --noEmit 通過；Astro check 41 files / 0 errors / 0 warnings / 0 hints。
- Builds：Portal static build 14 pages；GAS bundle 成功產生 dist/Code.js 與 dist/appsscript.json。
- Manual checks：anonymous adapter source 無 delete_message 或 on_message；archive reader/moderation 無 anonymous-reply capability；非 owner 為 0 writer calls / 0 audit；public fixture body 無 actor ID；mention suppression 為 true；private audit 無 body 欄位。
- Known warnings：Python 3.14 下既有 Course Assistant /health test 仍有 2 個來自 discord.py 2.7.1 的 asyncio.iscoroutinefunction deprecation warnings；Task 24 UI 沒有新增 warning。

## Diagnostics

- Discord modal 是 interaction response；modal submit 是另一個 interaction，適合私下收集文字並回 ephemeral acknowledgement，不需先發一般訊息。Task 24 adapter 依此分離 open 與 submit。來源：[Discord Interactions](https://docs.discord.com/developers/platform/interactions)。
- 現有 audit-event.schema.json 的 event enum 沒有 message reply/post 事件，metadata 也不允許 public message ID/display mode。Task 24 若硬套將違反 additionalProperties: false；因此使用 typed private port 並登記 U-010，等待正式 contract versioning。
- Writer protocol 現在要求 mention suppression，但 live Discord adapter 尚未存在；正式 adapter 必須把它落成 discord.AllowedMentions.none() 或等價 deny-all 行為，不能只相信 fixture boolean。
- Button/View/Modal 是可建構的 discord.py UI prototype，但尚未由 CourseAssistantDiscordApp 註冊 persistent view，也沒有從 case post 發送 view；原因是 live identity mapper、case-number routing 與 adapter 尚未配置。
- Identity resolver 目前是 in-memory fixture；Discord OAuth binding／verified internal account 才能在 live 環境建立可信 ActorContext，不能直接把 Discord snowflake 當內部 owner ID。
- Discord write、private audit append、idempotency complete 是三個 side effects。若 writer 成功後 audit 失敗，operation 會標 FAILED 但可能已有公開訊息；禁止 blind retry，需 Task 32 reconciliation/outbox。

## Assumptions made

- Anonymous modal reply 只允許 case owner；staff 不會透過此流程冒用學生顯示身份。Staff 若需回覆，使用一般教學人員 reply flow。
- Task 24 的「authorized user」解釋為已由 trusted identity resolver 映射、且 internal user ID 等於 case owner；role 或 Discord channel permission 不取代此檢查。
- Course-alias mode 固定使用 onboarding 既有五位 nnmmm；fully anonymous mode 絕不附帶 alias。Real-name mode 不需要匿名 modal，未納入本 service。
- Modal body 上限採 1800 而非 Discord 理論 4000，為 bot label/Markdown 與未來 adapter 留出 2000-character message 限制空間。
- Audit 不保存 raw body；原文只存在 public bot message/後續受控 export。若未來法遵要求原文稽核，需 retention/privacy review，不在本 Task 擴權。
- Button 以 case ID 綁定；未來 user-facing routing 可改為公開 case number，但在送進 service 前必須解析為 allowlisted internal case ID。

## Risks and blockers

- 高：Live identity resolver、persistent view registration、case-number routing 與 Discord writer adapter皆未完成，不可連正式 server。Mitigation：Task 32 定義 authenticated interaction adapter，Task 30 加 contract/security tests。
- 高：Writer 成功、audit/idempotency 失敗有 partial-state 風險。Mitigation：durable outbox、provider reconciliation、public message ID unique operation marker，禁止盲目重送。
- 高：正式 audit contract 尚無匿名回覆事件。Mitigation：Task 29 決定最小 metadata/retention，Task 32 版本化 schema；private audit 永不公開。
- 中：User-provided body 仍可能包含自己輸入的姓名或 ID；系統只能保證不自動插入 actor identity。Mitigation：modal 顯示 privacy 提示、mention deny-all、Task 29 定義內容警示／redaction policy。
- 中：Persistent view 未註冊，process restart 後 fixture button 不會自動恢復。Mitigation：live adapter 依 case index 重建 allowlisted views，或改用 stable /calc reply + case-number route。
- 無阻擋 Task 25 fixture-only Private Support design 的問題。

## Questions for ChatGPT discussion

- Anonymous reply 的正式 audit event 應擴充共用 AuditEvent，還是建立更窄的 MessageOperationAudit contract？
- Persistent per-case button 與 /calc reply <case-number> 哪個應是主要入口；是否兩者都保留但共用同一 owner authorization？
- User 自行在匿名 body 輸入姓名、學號或 Discord mention 時，應只顯示警告、阻擋已知 pattern，還是允許使用者自行承擔揭露？
- Writer 成功但 audit timeout 時，應先查 operation marker／message nonce，再補 audit，還是由人工 reconciliation queue 處理？

## Recommended next action

執行 Task 25：建立 Private Support fixture-safe case design。沿用 Task 24 的 modal-only private input、trusted identity mapping、generic ephemeral error 與 metadata-only audit 原則，但必須使用獨立 case type／restricted mechanism，永不 fallback 到一般公開 thread，也不讓 Archive Reader 存取。

## Copy-paste handoff

Task 24 已完成 anonymous modal reply prototype。新增綁定 case 的 Discord button/view、discord.py 2.7 私密 modal（1–1800 字）、trusted Discord→internal actor fixture resolver、開啟與送出雙重 owner authorization、course alias nnmmm 與 fully anonymous「匿名同學」兩種明確顯示、mention suppression、bot-only public repost、ephemeral submitter confirmation、operation idempotency 及 metadata-only private audit。非 owner 為 0 writes/0 audit；公開 body 不含系統插入的 Discord username/user ID；audit 私下保留 internal actor、case、public message、display mode、時間但不保留 raw body；完全沒有「先發一般訊息再刪除」或 on_message。Task 24 8/8、完整 Pytest 78/78、Portal 25/25、GAS 44/44 全過；secret scan 313/0、mypy 43 files、Astro 41 files 零診斷；Portal 14 pages 與 GAS bundle build 成功。仍 mocked：live identity resolver、Discord writer、persistent view registration、case-number routing、durable audit/idempotency。現有 audit-event schema 沒有匿名回覆事件，已登記 U-010，待 Task 29/32 決定。建議下一步 Task 25 Private Support，維持 modal-only、deny-by-default、永不公開 fallback、reader 無存取權。
