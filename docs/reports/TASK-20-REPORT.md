# TASK-20 report — multi-bot responsibilities and permissions

## Outcome

Complete。`course_assistant`、`archive_reader`、`moderation`與`common`的責任、permissions/intents、commands、event ownership、token/config separation、service ports、duplicate policy、failure isolation、Portal/GAS boundary與single-bot reversal均已固定為本機prototype architecture；沒有建立Discord application、token、guild connection或remote resource。

## Summary

- `course_assistant`是唯一user interaction與Discord write owner：website-mediated posting、anonymous repost、case status、nickname/allowlisted role、Private Support write都由它負責。
- `archive_reader`只負責管理者明確指定且allowlisted的thread/history fetch；不註冊commands、不訂閱全域message events、不send/edit/delete、不管理role/nickname/status。
- Reader最低channel permissions只有`VIEW_CHANNEL` + `READ_MESSAGE_HISTORY`；為讀取content/embeds/attachments，獨立application需核准`MESSAGE_CONTENT` capability。明確禁止`ADMINISTRATOR`及所有write/role/nickname/moderation permissions。
- Course assistant baseline只需`GUILDS` standard intent；`GUILD_MEMBERS`保持關閉且列為technical spike，`MESSAGE_CONTENT`關閉，因互動採slash command/modal/website command而非讀一般訊息。
- `moderation`在v1沒有application、token、permission、intent、command、event或service method；啟用前需新ADR/privacy review。
- `common`只是shared library，沒有Discord identity/token/product event handler；每個process只能讀自己的token variable。
- User-facing commands只由course assistant在`/calc` namespace註冊；reader只提供authorized admin/local service call，消除兩個application的duplicate commands。
- 每項input/event只有一個primary owner；interaction/operation/request ID配合durable idempotency/outbox，禁止兩個bots競速處理同一事件。
- 定義`CourseAssistantService`、`ArchiveReaderService`與narrow writer/reader ports；沒有含所有Discord methods的shared mega-client。
- Portal/browser直連Discord REST永久禁止；Portal/GAS→Discord transport尚未決定，暫以authenticated command API/queue port作preferred direction，Task 32再比較。
- 未來可在新ADR下以單一process/application組合writer+reader services，但接受union permissions風險，且仍維持narrow ports與單一event routing；不允許多process共用一token。

## Files changed

- `bots/ARCHITECTURE.md`：完整responsibility、permission/intent、command、event、credential、failure與reversal矩陣。
- `docs/architecture/BOT_SERVICE_INTERFACES.md`：application commands/services、narrow ports與error/idempotency contract。
- `bots/.env.example`：只保留shared non-secret fixture mode，不再暗示兩token共置。
- `bots/course_assistant/.env.example`、`bots/archive_reader/.env.example`：各自獨立token與allowlist config skeleton。
- `bots/README.md`及三個bot package README：責任、權限與credential boundary入口。
- `docs/decisions/ADR-0006-MULTI-BOT-SEPARATION.md`：將Task 20矩陣與未決部署問題同步進accepted prototype ADR。
- `docs/architecture/CONTEXT.md`：新增未決/mock authenticated command boundary，沒有browser→bot token路徑。
- `docs/architecture/COMPONENTS.md`：更新bot責任/非責任與跨元件owner rules。
- `docs/architecture/README.md`：文件導航。
- `docs/decisions/UNRESOLVED.md`：新增transport、Guild Members intent與Private Support mechanism三項未決問題。
- `docs/reports/TASK-20-REPORT.md`：本報告。

## Commands executed

- 只讀查閱Discord官方Gateway intents、permissions、Message resource與interactions文件。
- `sed`、`rg`、`find`檢視Task/ADR/architecture/bot scaffold與驗收關鍵字。
- `npx prettier --write <Task 20 Markdown files>`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `git diff --check`與`rg`檢查whitespace、owner/permission/token invariants。

沒有安裝/註冊Discord application、產生OAuth URL、邀請bot、請求privileged intent、注入token、開啟Gateway、呼叫Discord REST、發送訊息、建立role/channel或部署process。

## Verification

- Tests：完整repository仍為GAS Vitest 6 files / 44 tests、Portal Vitest 5 files / 25 tests、Pytest 36 tests全部passed；Task 20是architecture-only，沒有新增runtime test。
- Linters/type checks：完整root check通過；secret scan 275 candidate files / 0 findings；Prettier、Ruff lint/format、GAS strict tsc、Astro check 41 files / 0 errors / 0 warnings / 0 hints、mypy 9 source files全部成功。
- Builds：不適用；沒有新增runtime dependency或Discord executable。
- Manual checks：responsibility matrix每個bot capability只有一個`P`；reader permission row明列`MANAGE_ROLES`/`MANAGE_NICKNAMES`/send/admin forbidden；兩份bot-specific `.env.example`各只有自己的token variable；single-bot section保留interfaces並禁止competing processes。

## Diagnostics

- Discord官方文件指出`MESSAGE_CONTENT`影響跨API的content、embeds、attachments、components與polls，不只Gateway event；因此on-demand reader仍需該privileged capability，但不需要訂閱`GUILD_MESSAGES`。
- Discord `Get Channel Message`/history讀取要求`VIEW_CHANNEL`與`READ_MESSAGE_HISTORY`；reader不需send permission。來源：[Message resource](https://docs.discord.com/developers/resources/message)。
- `MANAGE_ROLES`與`MANAGE_NICKNAMES`仍受role hierarchy限制；course assistant最高role必須高於target/allowlisted course roles，不能用`ADMINISTRATOR`繞過。來源：[Permissions](https://docs.discord.com/developers/topics/permissions)。
- Gateway privileged intents必須在Developer Portal啟用，規模提高後可能需要approval；本Task只文件化，未申請或啟用。來源：[Gateway intents](https://docs.discord.com/developers/events/gateway)。
- Reader能看到原始內容/attachments，是高敏感read surface；channel overwrite必須只允許可匯出的一般case範圍，Private Support預設不可見。
- Interaction delivery可走Gateway或HTTP，但正式transport/host尚未選擇；本架構的service boundary不綁定其中之一。

## Assumptions made

- 第一版course assistant採slash commands/components/modals與internal website commands，不解析一般成員訊息，因此不需Message Content intent。
- Targeted nickname/role操作優先使用interaction/authenticated command已知的member ID；除非Tasks 21/22實證需要member lifecycle/list，否則不開Guild Members intent。
- Case status存於case service，Discord只呈現狀態；baseline不以`MANAGE_THREADS`作狀態機必要條件。
- Archive reader由local/admin flow明確呼叫，不在Discord註冊export command，降低reader interaction/write需求。
- Single-bot是reversal option而非目前deployment；若採用需新ADR與union permission review。

## Risks and blockers

- 高度：`MESSAGE_CONTENT`使reader可取得allowlisted channels中的user content與attachments；必須用channel overwrites、manager authorization、retention與audit限制，Task 29前不可production啟用。
- 高度：Portal/GAS→bot transport/auth尚未決定；不可讓browser或public GAS route持有/代理bot token。Mitigation：Task 32比較dedicated backend/queue與narrow GAS adapter。
- 高度：Private Support Discord mechanism未定；reader預設完全不可見，Task 25只做fixture-safe design。
- 中度：Course assistant的role/nickname permissions有較大寫入風險。Mitigation：allowlisted IDs、role hierarchy、membership authority port、operation id與audit。
- 中度：Durable idempotency/outbox尚未實作；Task 21只建立protocol/test doubles，實際storage在integration plan前仍是blocker。
- 無阻擋Task 21本機common core工作的問題。

## Questions for ChatGPT discussion

- Portal/GAS→course_assistant應使用dedicated authenticated backend、queue/webhook，還是narrow GAS adapter？由誰host與rotate credential？
- Course assistant的targeted member fetch能否完全避免Guild Members intent；實際guild規模與member lifecycle需求為何？
- Archive reader應是REST-only worker還是保留Gateway connection；Message Content privileged intent由誰申請/審核？
- Private Support採private thread、restricted channel或backend-only representation？是否應永遠排除reader application？
- 單bot營運成本是否真的優於兩application的least-privilege收益；接受何種union blast radius？

## Recommended next action

執行Task 21：將本Task的boundaries落成strict typed Python common core，包括per-bot config/token isolation、structured redacted logging、contract models、protocols、fixture clients與idempotency helpers，不連Discord。

## Copy-paste handoff

Task 20已完成多bot架構。course_assistant是唯一interaction/write/role/nickname owner；archive_reader只做管理者明確指定的allowlisted thread fetch，最低permissions為View Channel + Read Message History，為讀content/embeds/attachments需自己的Message Content capability，但沒有commands、message event subscription、send、role或nickname權限；moderation在v1完全沒有application/token/intents；common只是library、不持credential。Commands只用course assistant的/calc namespace，每個event有唯一owner與operation-ID idempotency；定義了narrow CourseAssistantService/ArchiveReaderService及writer/reader ports。Browser直連Discord永遠禁止，Portal/GAS transport留到Task 32，暫以authenticated backend/queue port建模。未來可用新ADR合併成單process bot，但不能多process共token，且仍保留capability interfaces。完整repo tests維持GAS 44/44、Portal 25/25、Pytest 36/36，secret scan 275 files/0 findings。未建立Discord app/token、未連Gateway。主要未決是transport、Guild Members intent、reader topology、Private Support mechanism及single-bot blast radius。建議下一步Task 21 Python common core。
