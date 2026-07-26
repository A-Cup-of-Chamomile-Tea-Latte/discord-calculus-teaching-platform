# TASK-21 report — shared Python bot core and fixture mode

## Outcome

Complete。Typed per-bot environment config、secret-safe structured logging、graceful lifecycle、fixture/dry-run mode、JSON contract registry、case/thread mapping repository protocol、separate Discord reader/writer abstractions、error taxonomy、health projection、idempotency helper與network-free fake client全部完成；package可在無token、repository外的工作目錄import，未連Discord。

## Summary

- `load_course_assistant_config`與`load_archive_reader_config`分別只接受自己的token/config names；若另一bot token共置會fail closed。
- 安全預設`BOT_RUNTIME_MODE=fixture`；`fixture`與`dry-run`模式禁止token，`live`模式要求own token、guild與channel allowlist，reader另要求明確`MESSAGE_CONTENT_ENABLED=true`。
- `SecretValue`的`repr`/`str`固定redacted，只有provider boundary可明確`reveal()`；config dataclass repr不含token。
- `StructuredLogger`每行輸出一個compact JSON object，對registered secret values、token/secret/password/api-key suffix與code/authorization等sensitive keys遞迴redact。
- `LifecycleManager`依序startup、逆序shutdown；startup中途失敗會清理已啟動components，stop失敗仍繼續清理其他components；提供shutdown event helper。
- `build_health`只投影component、mode、ready/network flags與allowlist count，不回傳token或raw guild/channel IDs。
- `ContractRegistry`從本機`contracts/schemas`建立Draft 2020-12 registry，驗證single value/record fixtures、拒絕path traversal schema name，錯誤只回rule/location而不回顯被拒絕的原始值。
- `CaseThreadMappingRepository`、`DiscordThreadReader`與`DiscordCourseWriter`是分離protocols；沒有shared mega-client。
- `FakeDiscordClient`完全記憶體運作，支援thread page fetch及recorded writer operations；`InMemoryCaseThreadMappingRepository`維持one thread→one case。
- `InMemoryIdempotencyStore`以bot namespace隔離operation state，提供begin/complete/fail deterministic fixture behavior。
- Error taxonomy涵蓋config、contract、authorization、not found、conflict、rate limit、provider unavailable、not configured與lifecycle。
- `jsonschema`移到main runtime dependency，setuptools明確discover `bots*`/`tools*` packages；三個future bot packages有無副作用`__init__.py`，可同時import而不循環。

## Files changed

- `bots/common/config.py`：typed named configs、runtime modes、Discord ID/allowlist validation與token separation。
- `bots/common/structured_logging.py`：recursive secret redaction與compact JSON logger。
- `bots/common/lifecycle.py`、`health.py`：graceful component orchestration與safe health projection。
- `bots/common/contracts.py`：local JSON Schema registry、load/validate與safe diagnostics。
- `bots/common/models.py`、`ports.py`：thread/message/attachment/mapping/health models及narrow protocols。
- `bots/common/errors.py`：shared error taxonomy。
- `bots/common/idempotency.py`：idempotency protocol與in-memory fixture store。
- `bots/common/testing.py`：fake Discord read/write client、mapping repository、lifecycle component。
- `bots/common/__init__.py`、`README.md`：safe exports與模組導航。
- `bots/course_assistant/__init__.py`、`bots/archive_reader/__init__.py`、`bots/moderation/__init__.py`：無副作用package boundaries。
- `bots/archive_reader/.env.example`：明列Message Content capability flag，預設false。
- `tests/bots/test_common_*.py`：18個config/log/lifecycle/contract/fake/idempotency tests。
- `pyproject.toml`：`jsonschema`成為runtime dependency，明確package discovery。
- `docs/reports/TASK-21-REPORT.md`：本報告。

## Commands executed

- `python -m ruff format bots/common tests/bots`。
- `python -m ruff check bots/common tests/bots`。
- `python -m mypy bots/common tests/bots`與完整`python -m mypy`。
- `python -m pytest tests/bots -q`。
- `python -m pip install -e '.[dev]' --no-deps`：重建editable package，不安裝/更新dependency。
- 從`/tmp`、unset兩個token與mode後執行`python -c 'import bots.common; …'`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `git diff --check`與`rg`檢查test token字串、Discord library/client import與whitespace。

沒有安裝`discord.py`、建立live adapter、讀取真實`.env`、要求token、開Gateway、呼叫Discord REST、DNS/network fixture、產生Discord application或寫入遠端。

## Verification

- Tests：Task 21 Pytest 18/18 passed；完整Pytest 54/54、GAS Vitest 44/44、Portal Vitest 25/25全部passed。
- Linters/type checks：完整root check通過；secret scan 294 candidate files / 0 findings；Ruff lint/format全部成功；strict mypy 27 source files無問題（Task-specific檢查21 files）；Astro 41 files / 0 errors / 0 warnings / 0 hints；GAS tsc通過。
- Builds：editable wheel成功建立並安裝，wheel 3,339 bytes；`jsonschema`未重下載（`--no-deps`）。
- Manual checks：從`/tmp`且無token環境import成功並回`fixture`；test-only fake token strings只存在`tests/bots`，不在`bots`/docs/fixtures；`bots/common`沒有`discord.py`/`import discord`/real client construction。

## Diagnostics

- Main package現在真的依賴`jsonschema`，不再只靠dev extra；否則`bots.common`從clean production install匯入`ContractRegistry`會失敗。
- `FakeDiscordClient`為測試方便同時實作reader/writer methods，但production services只應以narrow protocol注入其中一面；它不是single-bot architecture決策。
- `InMemoryIdempotencyStore`與mapping repository只保證單process fixture behavior，不是durable/atomic production storage。
- Structured logger只能保護經由它輸出的records；未來`discord.py`/HTTP library的第三方logger仍需額外filter與handler policy。
- Contract validator錯誤刻意不含raw instance/message，降低content/PII進log風險，但diagnostic detail較少；operator可在受保護本機重現。
- Lifecycle helper沒有自行安裝OS signal handlers；host需把SIGINT/SIGTERM轉成`request_shutdown()`並在Task 30整合測試。
- Config只驗證Discord IDs形狀與allowlists，不代表guild/channel/role存在或caller被授權；live adapter啟動時仍需provider-side capability check。

## Assumptions made

- 完全缺少environment時採`fixture`是最安全且可import的預設；任何live connection都要明寫`BOT_RUNTIME_MODE=live`。
- Dry-run與fixture都不需要、也不允許token；未來若要authenticated no-write smoke mode，需新增明確mode與ADR，而非放寬dry-run。
- Discord snowflake以17–20位數字字串驗證；不轉integer。
- Reader live config必須明確承認Message Content capability，避免部署者只填token就意外擴大read surface。
- JSON contract runtime validation是bot ingress/egress必要能力，因此`jsonschema`屬main dependency。

## Risks and blockers

- 高度：沒有real `discord.py` adapter、permission/intents probe、rate-limit/reconnect behavior或provider audit；不可live啟動。
- 高度：沒有durable idempotency/outbox或mapping repository；重啟後in-memory state消失。Task 22/23仍只能fixture-safe。
- 中度：第三方logs可能繞過`StructuredLogger`。Mitigation：live composition時統一logging filters、禁HTTP body/debug與provider token output。
- 中度：`SecretValue.reveal()`是刻意的provider escape hatch；code review需限制呼叫位置，並禁止把結果放入exceptions/logs。
- 中度：Package沒有Python lockfile，只有版本範圍；Task 30 CI需在Python 3.12及目前3.14重現install/tests。
- 無阻擋Task 22本機course assistant fixture service的問題。

## Questions for ChatGPT discussion

- Durable idempotency/outbox與case-thread mapping應由哪個store承擔，是否與GAS/Sheets分離？
- Live host應如何統一攔截`discord.py`與HTTP library logs，且保留足夠rate-limit diagnostics？
- 是否需要新增authenticated-but-no-write staging mode，還是fixture/dry-run/live三態足夠？
- Contract validation failure在production應保留哪些safe diagnostic fields與metrics？

## Recommended next action

執行Task 22：在`course_assistant` package以Task 21 narrow writer/config/fake/idempotency ports實作slash-command-shaped fixture handlers、website-mediated case post、approved nickname/role及case status flow；不import或連線Discord live client。

## Copy-paste handoff

Task 21已完成shared Python bot core：有course/archive分離typed env config，預設fixture且fixture/dry-run禁止token，live缺token/guild/channel會給actionable error，reader live另需明確Message Content flag；SecretValue與JSON logger會redact token/authorization/code等敏感值。另有reverse-order lifecycle、safe health、Draft 2020-12 contract registry、case-thread mapping protocol、分離reader/writer protocols、error taxonomy、namespaced idempotency，以及完全記憶體fake Discord client/repository。jsonschema已移到runtime dependency，bots/tools package discovery可建立editable wheel；從/tmp無tokenimport成功並回fixture，future bot packages可同時import無circular。Task專屬18/18、完整Pytest 54/54、GAS 44/44、Portal 25/25全過；secret scan 294 files/0 findings、mypy 27 files、Ruff/Astro/tsc全過。尚無discord.py/live adapter、durable store/outbox、provider permission probe或第三方log filter，不可live。建議下一步Task 22 course assistant fixture service。
