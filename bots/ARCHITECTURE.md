# Discord multi-bot architecture

本文件是 prototype capability boundary，不代表已建立 Discord application、核准 intents 或完成 production deployment。官方平台規則於 2026-07-19 依 [Discord Gateway intents](https://docs.discord.com/developers/events/gateway)、[Permissions](https://docs.discord.com/developers/topics/permissions) 與 [Message resource](https://docs.discord.com/developers/resources/message) 核對；實際安裝前必須重查。

`dump_bot` 是 2026-07-23 起的 canonical 產品名稱。現有 `bots.archive_reader`、`ArchiveReaderService` 與 `ARCHIVE_READER_DISCORD_TOKEN` 暫時保留為程式相容層；它們不是第三隻 bot，也不允許另一份 token 或重複 runtime。

## Runtime identities

| Package            | Discord identity                | Primary purpose                                                          | Explicit non-purpose                                                        |
| ------------------ | ------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| `course_assistant` | own application + own bot token | interactions and authorized Discord writes                               | bulk/history export, silent global message monitoring, teaching analysis    |
| `dump_bot`   | own application + own bot token | manager-requested read/fetch for an allowlisted case thread              | commands, replies, roles, nicknames, status mutation, continuous monitoring |
| `moderation`       | no application/token in v1      | reserved package and decision boundary only                              | any current event subscription or moderation action                         |
| `common`           | never a Discord identity        | config types, contracts, logging, idempotency helpers, adapter protocols | token ownership, event handlers, product workflow                           |

Shared code never means shared credentials. A process receives only its own token variable; it must fail startup if another bot's token variable is present in the same runtime configuration.

## Responsibility matrix

`P` is the sole primary owner; `—` means the capability is forbidden or absent.

| Capability                                      | course_assistant | dump_bot | moderation | common / external                                |
| ----------------------------------------------- | :--------------: | :------------: | :--------: | ------------------------------------------------ |
| Slash commands, buttons, selects, modals        |        P         |       —        |     —      | common provides framework-neutral types only     |
| Website-mediated general question post          |        P         |       —        |     —      | later authenticated backend invokes service      |
| Anonymous modal/website reply repost            |        P         |       —        |     —      | policy/identity verified before command          |
| Case status write and Discord status message    |        P         |       —        |     —      | case store remains source for workflow state     |
| Course nickname and approved role assignment    |        P         |       —        |     —      | membership authority is external to Discord      |
| Private Support Discord write                   |        P         |       —        |     —      | mechanism unresolved until Task 25               |
| Fetch one explicitly selected thread/history    |        —         |       P        |     —      | caller must be an authorized manager flow        |
| Map fetched messages to `CaseMessage`           |        —         |       P        |     —      | common contract mapper may be reused             |
| Persist local export files                      |        —         |       —        |     —      | explicit local export tool owns filesystem write |
| Continuous `MESSAGE_CREATE` monitoring          |        —         |       —        |     —      | prohibited in v1                                 |
| Moderation actions/events                       |        —         |       —        |     —      | future ADR required                              |
| OAuth, email, activation code, enrollment proof |        —         |       —        |     —      | Portal/GAS/approved membership service           |
| Token loading and redaction                     |  own token only  | own token only |     —      | common supplies validated loader, no values      |

Every mutable capability has one primary owner. `dump_bot` returns data; it never silently delegates a failed read to `course_assistant`, because that would widen the writer token's read surface.

## Discord permissions

Permissions are assigned by bot role and narrowed again with channel/category overwrites. `ADMINISTRATOR` is forbidden for every bot.

| Discord permission                                                                                      | course_assistant                                                          | dump_bot                                                | Reason / boundary                                      |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------ |
| `VIEW_CHANNEL`                                                                                          | required only in managed interaction/case/support channels                | required only in allowlisted exportable general-case channels | denying it implicitly removes channel access           |
| `SEND_MESSAGES`                                                                                         | required in bot-output and forum parent channels                          | forbidden                                                     | forum creation and bot posts; reader cannot write      |
| `SEND_MESSAGES_IN_THREADS`                                                                              | required in managed case threads                                          | forbidden                                                     | replies/status posts                                   |
| `READ_MESSAGE_HISTORY`                                                                                  | required where replying/reconciling its own case posts                    | required                                                      | Discord requires it for history and referenced replies |
| `MANAGE_NICKNAMES`                                                                                      | required for approved course alias operation                              | forbidden                                                     | bot role must be above target member                   |
| `MANAGE_ROLES`                                                                                          | required only for allowlisted course roles                                | forbidden                                                     | bot can only grant/edit roles below its highest role   |
| `EMBED_LINKS`                                                                                           | optional; plain text remains valid fallback                               | forbidden                                                     | not required for domain behavior                       |
| `ATTACH_FILES`                                                                                          | off by default; future allowlisted forwarding only                        | forbidden                                                     | reader fetches metadata/URLs but does not upload       |
| `MANAGE_THREADS`                                                                                        | off by default; add only if Task 22 proves lock/archive/tag flow needs it | forbidden                                                     | case status must not imply broad thread moderation     |
| `CREATE_PRIVATE_THREADS`                                                                                | off until Task 25 chooses a mechanism                                     | forbidden                                                     | no private-support topology is pre-approved            |
| `MANAGE_MESSAGES`, `MANAGE_CHANNELS`, `MANAGE_GUILD`, `MENTION_EVERYONE`, `BAN_MEMBERS`, `KICK_MEMBERS` | forbidden                                                                 | forbidden                                                     | outside current capability ownership                   |

The reader's minimum install permissions are therefore `VIEW_CHANNEL` + `READ_MESSAGE_HISTORY`, scoped by channel overwrite. It never receives role/nickname management, send, thread-management, moderation or administrator permissions.

## Gateway intents

| Intent                                                    | course_assistant                                                                                          | dump_bot                                                            | moderation | Decision                                                              |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------- |
| `GUILDS`                                                  | baseline standard intent                                                                                  | only if a Gateway connection is retained                                  | none       | channel/role metadata and readiness                                   |
| `GUILD_MEMBERS`                                           | off by default; privileged technical spike only if member lifecycle/list subscription is proven necessary | off                                                                       | none       | targeted membership operations should avoid broad member events/cache |
| `GUILD_MESSAGES`                                          | off                                                                                                       | off                                                                       | none       | no global message event ownership                                     |
| `MESSAGE_CONTENT`                                         | off                                                                                                       | required privileged capability for content/embeds/attachments across APIs | none       | only reader handles explicit content fetch                            |
| reactions, typing, presences, DMs, voice, auto-moderation | off                                                                                                       | off                                                                       | none       | no v1 capability needs them                                           |

Discord documents that `MESSAGE_CONTENT` affects content, embeds, attachments, components and polls across APIs, not just Gateway events. `dump_bot` therefore needs the capability even with on-demand HTTP history fetch, but it still does not subscribe to `GUILD_MESSAGES`. Whether a REST-only reader can avoid a Gateway session remains a separate pre-live test-guild gate.

## Command namespace

Only `course_assistant` registers user-facing commands, under one `/calc` root where Discord/library support permits subcommands:

- `/calc ask`：open a general-question modal;
- `/calc reply`：anonymous-safe reply modal owned by Task 24;
- `/calc status`：authorized case-status operation;
- `/calc join`：start an approved membership/nickname/role operation, never self-attest enrollment;
- `/calc privacy`：show privacy guidance/settings entry;
- `/calc support`：Private Support entry, mechanism deferred to Task 25.

`dump_bot` registers no Discord command. Authorized managers invoke its `fetch_selected_thread` service through a local/admin backend or CLI. `moderation` reserves no namespace until a future ADR. This prevents two applications from showing duplicate commands.

## Event ownership and duplicate prevention

| Input/event                                                | Primary owner                 | Duplicate policy                                                                                   |
| ---------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------- |
| Discord interaction create for `/calc`, component or modal | course_assistant              | interaction ID is an idempotency key; one command registry and one handler                         |
| Internal website post/reply/status command                 | course_assistant service      | caller-supplied operation ID; durable compare-and-set before Discord write                         |
| Member join/update/remove Gateway events                   | no owner in baseline          | enabling requires ADR/technical spike; course_assistant would be sole owner                        |
| Message create/update/delete Gateway events                | no owner                      | prohibited continuous monitoring; archive fetch is explicit HTTP/read adapter call                 |
| Manager-selected thread fetch request                      | dump_bot                | request/export ID + case/thread allowlist; repeated request returns same snapshot/cursor semantics |
| Bot ready/disconnect/health                                | each runtime owns only itself | never used for product mutation                                                                    |

Handlers acknowledge/validate first, then call a service with an operation ID. Retryable side effects use an outbox or idempotency store; process-local sets are test helpers only. A duplicate interaction may return the previous result, but it must not create a second post, role grant, alias allocation or status transition. Events are never broadcast to both bots for “whichever responds first.”

## Token and configuration separation

- `course_assistant` reads only `COURSE_ASSISTANT_DISCORD_TOKEN`; `dump_bot` reads only `ARCHIVE_READER_DISCORD_TOKEN`.
- Each token is injected into a separate process/runtime secret store. Do not create one `.env` containing both production tokens.
- Guild/channel/role IDs are bot-specific allowlists where capabilities differ; IDs are configuration, not authorization by themselves.
- `common` accepts already-validated config objects and never imports both token variable names into a shared singleton.
- Logs may include bot name, operation ID, outcome and latency; never token, authorization header, raw interaction body or Private Support content.
- Token rotation/revocation is independent. A token mismatch must fail closed; one bot must not fall back to another token.
- Multiple competing processes must not use one token. Explicit Discord sharding is a separate deployment design and does not change application-level event ownership.

## Failure isolation

| Failure                      | Allowed effect                        | Required behavior                                                                                    |
| ---------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| course_assistant unavailable | interactions/writes pause             | archive read remains possible; no reader-to-writer privilege escalation                              |
| dump_bot unavailable   | export/fetch pauses                   | interactions and case writes continue; local tool reports retryable read failure                     |
| GAS/Sheets unavailable       | metadata write/reconciliation pauses  | Discord writes requiring durable state fail closed or enter an explicit outbox; no untracked write   |
| Discord rate limit/outage    | affected bot pauses/retries boundedly | honor provider retry metadata, keep idempotency key, no tight loop                                   |
| common library regression    | potentially both packages             | independent deployment/version pinning, contract tests and rollback per runtime                      |
| one token compromised        | that bot's permissions/channels only  | revoke only that token, audit affected operations, do not rotate/share the other token automatically |

Health checks are per runtime. Queues/outboxes, circuit breakers and retry budgets are separate. Private Support failures never fall back to a public channel.

## Portal / GAS / Discord path

Current state is deliberately unresolved:

- Browser → Discord REST with a bot token is forbidden.
- Portal → GAS → Discord REST is not implemented or selected; putting a writer token in Apps Script would add a sensitive credential, execution/quota and audit boundary.
- Provisional preferred direction is Portal/GAS → authenticated command API/queue → `course_assistant` service, with the bot token only in its runtime. `dump_bot` is invoked separately by an authorized manager/export flow.
- The fixture prototype does not select a production transport. A dedicated backend, authenticated queue/webhook and narrowly scoped GAS adapter remain choices for a separately approved production gate; until then all cross-system commands are fixture ports.

## Future single-bot option

`CourseAssistantService` and `ArchiveReaderService` depend on separate writer/reader ports, not process globals. A future host may compose both services into one process/application, but only under a superseding ADR that accepts the union permission/token blast radius. Even then:

- command/event ownership remains singular;
- reader methods cannot call writer methods;
- capability allowlists remain separate in code and audit;
- one event is routed once through an explicit registry;
- a single token is used by one coordinated process, never by competing processes.

This preserves a reversible single-bot deployment without pretending that two independent programs may safely share credentials.
