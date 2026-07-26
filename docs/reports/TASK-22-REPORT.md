# TASK-22 report — Course Assistant bot skeleton

## Outcome

Complete。使用`discord.py 2.7.1`建立fixture/dry-run Course Assistant command skeleton、`/health`、case post、`nnmmm`nickname/joining-order、membership/class roles、case status/tag、button/modal registration、Private Support hook及staff authorization；fixture無token可start，沒有Discord network、application、guild write或live adapter。

## Summary

- `CourseAssistantDiscordApp`建立真實discord.py `CommandTree`並註冊唯一top-level`/health`；intents只有`GUILDS=true`，`GUILD_MEMBERS=false`、`MESSAGE_CONTENT=false`。
- Fixture/dry-run `start()`只將local health設為READY，不呼叫`Bot.start()`；live mode明確回`NotConfiguredError`，不reveal token。
- Commands保持薄層：`/health`只呼叫service health projection並回ephemeral繁中狀態；其他初始surfaces以typed application service interfaces提供，等待後續interaction adapters。
- `create_case_post`驗證actor/case/operation/title/body，透過narrow writer建立thread、寫case-thread mapping與OPEN state，operation replay不重複Discord write。
- Pure `generate_course_alias`強制class code兩位數、joining order 1–999並輸出固定5位`nnmmm`；fixture repository依course/class順序分配，對同user idempotent。
- `apply_membership`只有staff user/role policy可呼叫；internal user ID與Discord user ID分離，writer以Discord snowflake設定nickname，再加allowlisted broad membership + class role。
- Constructor交叉檢查membership role policy只能使用bot config role allowlist，case parent只能使用channel allowlist。
- `update_case_status`只有staff可用，採expected-status compare-and-set、固定五種CaseStatus與safe tag ID，透過writer status/tag method呈現。
- `InteractionHookRegistry`提供unique button/modal names及單一Private Support creation hook；未設定Private Support時fail closed，不會fallback公開channel。
- Common idempotency `begin()`改回傳atomic acquisition decision，區分首次claim與in-progress/completed replay，避免兩coroutines都把同operation當首次。
- Course Assistant package沒有archive fetch/export、message event listener或moderation surface。

## Files changed

- `bots/course_assistant/models.py`：actor、case/membership/status/private-support commands與results。
- `bots/course_assistant/repositories.py`：pure alias、joining-order/case repository protocols與in-memory fixtures。
- `bots/course_assistant/permissions.py`：staff policy與membership/class role allowlist policy。
- `bots/course_assistant/hooks.py`：button/modal/private-support registration hooks。
- `bots/course_assistant/service.py`：case create、membership、status/tag、health與Private Support delegation。
- `bots/course_assistant/discord_app.py`：discord.py `/health` tree與network-free lifecycle。
- `bots/course_assistant/__init__.py`、`README.md`：exports、責任與fixture使用說明。
- `bots/common/ports.py`、`testing.py`：新增narrow status/tag writer method與fake recording。
- `bots/common/idempotency.py`：`BeginOperationResult(acquired)` atomic claim result。
- `tests/bots/test_common_fakes.py`：更新idempotency acquisition assertions。
- `tests/bots/test_course_assistant.py`：9個alias/allocation/case/membership/permission/status/hooks/app/leakage tests。
- `pyproject.toml`：加入`discord.py>=2.7.1,<3`runtime dependency。
- `docs/reports/TASK-22-REPORT.md`：本報告。

## Commands executed

- 只讀核對PyPI官方`discord.py`release/metadata。
- `python -m pip install 'discord.py>=2.7.1,<3'`至`/tmp`測試venv；安裝2.7.1及其runtime dependencies，未安裝voice extra。
- `python -m ruff format bots/common bots/course_assistant tests/bots`。
- `python -m ruff check …`與`python -m mypy …`。
- `python -m pytest tests/bots/test_course_assistant.py … -q`。
- `python -m pip install -e '.[dev]' --no-deps`重建editable package metadata。
- `python -c 'import discord; import bots.course_assistant; print(discord.__version__)'`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `rg`檢查archive/moderation/event/message-content與`bot.run`/`bot.start`責任洩漏。

沒有Discord login、token、application registration、OAuth invite、Gateway/REST call、command sync、guild/channel/thread/message/nickname/role/tag write或remote resource。

## Verification

- Tests：Task 22 Pytest 9/9 passed；完整Pytest 63/63、GAS Vitest 44/44、Portal Vitest 25/25全部passed。
- Linters/type checks：完整root check通過；secret scan 302 candidate files / 0 findings；Ruff lint/format成功；strict mypy 34 source files無問題；Astro 41 files / 0 errors / 0 warnings / 0 hints；GAS tsc通過。
- Builds：editable wheel成功建立，3,354 bytes；`discord.py.__version__ == 2.7.1`，Course Assistant package import成功。
- Manual checks：fixture app無tokenstart為READY，command tree只有`health`；guilds intent true、members/message content false；course package沒有`fetch_thread`、`export_thread`、`moderate_member`、`on_message`、`bot.run`或live `bot.start`。
- Warnings：Python 3.14測試出現2個來自`discord.ext.commands.core`的DeprecationWarning；上游仍呼叫預定Python 3.16移除的`asyncio.iscoroutinefunction`。未suppress，功能/tests仍成功。

## Diagnostics

- PyPI於2026-07-19核對的current release是`discord.py 2.7.1`（2026-03-03），metadata要求Python>=3.8並標示typed；本機Python 3.14可安裝/執行，但出現上述deprecation warnings。來源：[discord.py on PyPI](https://pypi.org/project/discord.py/)。
- `commands.Bot`可以在沒有token時安全construct command tree；真正network login只會發生在明確呼叫`start/run`，fixture runtime刻意不提供。
- Membership是多個Discord side effects（nickname + 2 roles）；fake成功不代表production atomic。中途失敗可能partial apply，需reconciliation/outbox。
- Status先更新case source state再呼叫Discord display writer；provider失敗會留下需reconcile的狀態差異。這是刻意保留source-of-truth優先，但尚無worker。
- In-memory joining order在單process內atomic/idempotent，無法防跨process同時分配；production repository需unique constraint/transaction。
- Private Support只有hook，沒有選定private thread/restricted channel/backend mechanism；不設定時安全拒絕。
- Button/modal目前只註冊domain hook names，沒有persistent `discord.ui.View`、custom IDs或interaction timeout handling；Tasks 24/25補齊。

## Assumptions made

- `/health`依Task 22使用top-level command；其他user-facing commands仍遵守Task 20的未來`/calc`namespace，尚未註冊。
- Course Assistant不讀一般message content；case body只來自validatedwebsite/interaction command，live adapter必須使用`allowed_mentions` deny-by-default。
- Staff authorization由upstream adapter建立的internal user ID + Discord role IDs判斷；Discord permissions本身不取代application authorization。
- Broad membership/class role IDs由config allowlist提供，service不建立或搜尋任意role。
- Case status固定沿用既有五種enum，不新增workflow state或任意Discord tag語意。

## Risks and blockers

- 高度：沒有live Discord adapter、command sync/auth mapper、permission/role-hierarchy preflight、durable mapping/idempotency/outbox或audit；不可連正式server。
- 高度：membership與status有跨providerpartial-failure風險。Mitigation：durable operation state、reconciliation及operator review，禁止blind retry。
- 高度：Private Support mechanism未決；hook永不fallback公開post，Task 25需deny-by-default design。
- 中度：discord.py 2.7.1在Python 3.14有upstream deprecation warning。Mitigation：Task 30同測3.12/3.14、追蹤上游，Python 3.16前升級或修正。
- 中度：joining-order max 999/班且production concurrency未解。Mitigation：database unique key `(course,class,order)` + user/course uniqueness。
- 中度：fixture writer在記憶體保存body供assert；production logs/audit不得保存raw content。
- 無阻擋Task 23本機archive reader fixture service的問題。

## Questions for ChatGPT discussion

- Membership partial failure的reconciliation順序：nickname、broad role、class role何者為commit marker？
- Case status應只存在backend，還是映射Discord forum tag；tag IDs/transition policy由誰管理？
- Course Assistant live adapter是否要完全HTTP interactions模式以避免Gateway，或保留GUILDS-only Gateway？
- Joining order由GAS/Sheets、獨立database或bot-local service分配？如何保證跨process唯一？
- `/health`應對所有成員可見、只對staff，還是公開但只回最小狀態？

## Recommended next action

執行Task 23：以Task 21的`DiscordThreadReader`、contract registry、mapping repository與fake snapshot建立explicit selected-thread archive reader；只讀allowlisted general case，不註冊commands、不持writer port、不連Discord。

## Copy-paste handoff

Task 22已完成discord.py 2.7.1 Course Assistant fixture skeleton：無token可start，CommandTree只有/health，intents僅GUILDS，members/message content皆關閉，live start明確拒絕。Service完成idempotent case post、pure nnmmm nickname（2位class+3位order）、joining-order repository、staff-only membership nickname+broad/class allowlisted roles、staff-only case status/tag、button/modal registration及fail-closed Private Support hook；internal user ID與Discord user ID分離，沒有archive/moderation/on_message責任。Task 9/9、完整Pytest 63/63、GAS 44/44、Portal 25/25全過；secret scan 302/0、mypy 34 files、Ruff/Astro/tsc全過，editable wheel 3,354 bytes。Python 3.14有2個discord.py上游asyncio deprecation warnings但功能通過。尚無live adapter、command sync、durable store/outbox、atomic membership/status reconciliation或Private Support mechanism，不可連server。建議下一步Task 23 archive reader fixture service。
