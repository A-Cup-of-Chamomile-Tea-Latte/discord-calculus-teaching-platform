# TASK-23 report — least-privilege Archive Reader skeleton

## Outcome

Complete。已建立只有明確觸發讀取能力的 Archive Reader fixture-first service，包含 health、案件編號解析、bounded pagination、管理者授權、`/dump`/`/follow` 本機管理介面、last-exported-message checkpoint、attachment metadata 轉換與 local export handoff。沒有連接 Discord、註冊 Discord command、建立 background polling、下載 attachment 或寫入任何 Discord resource。

## Summary

- `ArchiveReaderService.resolve_thread_id()` 只在 manager 授權後解析一個 `GENERAL` case number，並驗證 guild、parent channel allowlist、case/mapping 一致性。
- `dump()` 在每次明確請求時從 thread 起點分頁讀取；`follow()` 在每次明確請求時只從上次成功交付的 Discord message ID 後讀取。
- Pagination 每頁 1–100 則、預設最多 100 頁，對 wrong thread、duplicate message、empty page with cursor、invalid/repeated cursor 與超過頁數上限 fail closed。
- Checkpoint 只在 `ExportHandoffSink.accept()` 成功後更新；沒有 timer、scheduler、sleep、Gateway event subscription 或自動 mirror。
- `ArchiveMessageMapper` 將 Discord snapshot 轉為已通過 `case-message.schema.json` 的 record；Discord author 必須有明確內部 user/display/analysis policy mapping，未知作者 fail closed。
- Attachment 只交付 ID、filename、media type、size；不交付 CDN URL、不下載內容，也不偽造無法從 Discord 得到的 SHA-256。
- `ArchiveReaderAdminApp` 提供 `/dump` 與 `/follow` 同名的本機管理介面與 health lifecycle；它故意不是 `discord.py` command tree，因此 reader 不需 interaction response 寫入權限。
- Request ID 使用 common idempotency store；已完成的相同 request 回傳 duplicate handoff，不重讀 thread。
- `FakeDiscordClient` 新增 read-call recording，可驗證頁數、cursor、授權前無讀取與全程無寫入。

## Files changed

- `bots/archive_reader/models.py`：case、manager、identity policy、contract record、export command/handoff 與 follow checkpoint 型別。
- `bots/archive_reader/permissions.py`：內部 user ID/Discord role ID allowlist manager policy。
- `bots/archive_reader/repositories.py`：case index、identity policy、checkpoint、handoff sink ports 與 in-memory fixture repositories。
- `bots/archive_reader/mapping.py`：Discord snapshot 至 CaseMessage contract 的 fail-closed mapper，並排除 attachment URL。
- `bots/archive_reader/service.py`：案件解析、明確 dump/follow、bounded pagination、handoff/checkpoint 順序與 idempotency。
- `bots/archive_reader/admin_app.py`：network-free lifecycle、health 與本機 `/dump`/`/follow` 介面。
- `bots/archive_reader/__init__.py`：更新 package 說明。
- `bots/archive_reader/README.md`：說明介面、最小權限、無監看語意、資料邊界與現有限制。
- `bots/common/testing.py`：新增 `FakeReadCall` 與 fixture read-call trace。
- `tests/bots/test_archive_reader.py`：7 個 Task 23 tests，覆蓋多頁、incremental checkpoint、duplicate request、attachment metadata、manager/private 阻擋、fixture app、無 background scheduler 與 cursor failure。
- `docs/reports/TASK-23-REPORT.md`：本報告。

## Commands executed

- `sed`/`rg` 查閱 Task 23、Task 20 架構決定、common ports/config/fakes、CaseMessage schema 與 fixtures。
- `ruff format bots/common/testing.py bots/archive_reader tests/bots/test_archive_reader.py`。
- `ruff check bots/common/testing.py bots/archive_reader tests/bots/test_archive_reader.py`。
- `mypy bots/common/testing.py bots/archive_reader tests/bots/test_archive_reader.py`。
- `pytest -q tests/bots/test_archive_reader.py tests/bots/test_common_fakes.py`。
- `npm run check`。
- `npm run build`。
- `git status --short`、`git diff --check` 與 `rg` 的 no-scheduler/no-writer/no-Discord-app invariant 檢查。

沒有發送 Discord 訊息、讀取真實 thread、下載 attachment、設定 token、建立 Gateway/REST connection、寫入外部系統或部署。

## Verification

- Tests：Task 23 定向檢查 10/10 passed（7 archive reader + 3 common fake）；完整 Portal Vitest 25/25、GAS Vitest 44/44、Pytest 70/70 passed。
- Linters/type checks：secret scan 309 candidate files / 0 findings；Prettier 通過；Ruff lint/format 通過；strict mypy 41 source files 無問題；GAS `tsc --noEmit` 通過；Astro check 41 files / 0 errors / 0 warnings / 0 hints。
- Builds：Portal static build 成功，14 pages；GAS bundle 成功產生 `dist/Code.js` 與 `dist/appsscript.json`。
- Manual checks：reader source 無 `create_task()`、`asyncio.sleep`、`tasks.loop`、Discord client/bot 或 writer methods；未授權與 Private Support tests 的 read calls 均為 0；attachment contract 無 URL。
- Known warnings：Python 3.14 下現有 `discord.py 2.7.1` course-assistant health-command test 仍有 2 個來自上游 `asyncio.iscoroutinefunction` deprecation warnings；與 Task 23 reader 無關且未壓制。

## Diagnostics

- Discord message history 讀取的最小 channel permissions 為 `VIEW_CHANNEL` + `READ_MESSAGE_HISTORY`；本服務不需 send/manage/admin permissions。來源：[Discord Message resource](https://docs.discord.com/developers/resources/message)。
- Discord `MESSAGE_CONTENT` privileged intent/capability 影響 message content、embeds、attachments 等欄位；即使未來採 targeted REST-only reader，live application 仍需正式核對此能力，但本 Task 沒有申請或啟用。來源：[Discord Gateway intents](https://docs.discord.com/developers/events/gateway)。
- CaseMessage contract 要求非空 `body`，但 Discord 可有 attachment-only message。本版不自行填入虛構文字，而是 fail closed；Task 26 需選擇 contract extension 或明確 placeholder policy。
- In-memory sink、checkpoint 與 idempotency 不具備單一 durable transaction。順序已確保 sink 失敗不推進 checkpoint，但 process 在 sink 成功後崩潰仍可留下部分狀態；Task 26/32 需 durable outbox/transaction design。
- Manager authorization 目前是injected allowlist policy；live identity provider、audit event 與credentialed admin transport尚未決定。

## Assumptions made

- 沿用 Task 20 accepted architecture：Course Assistant 是唯一 Discord user-facing command owner；Task 23 要求的 `/dump`/`/follow` 解釋為 local/admin command-shaped interface，不在 reader application 註冊 Discord slash commands。這是可逆假設；若改為 Discord interaction，必須新增 command ownership、interaction response 與權限審查。
- `last_exported_message_id` 保存原始 Discord message ID，因其同時是 history pagination cursor；CaseMessage 的內部 ID 仍另行穩定映射為 `msg_discord_<id>`。
- Follow 在沒有新訊息時仍產生 0-message handoff，但不更新 checkpoint，供本機工具明確呈現「已檢查、無新項目」。
- Discord 無原生 attachment SHA-256 時不下載計算；optional `sha256` 欄位留給後續受控 local pipeline。
- Case index 是已審核的 metadata source；Private Support 以和不存在相同的 error 處理，避免案件存在性側信道。

## Risks and blockers

- 高：Live reader 可讀取 allowlisted channel 的原始內容與 attachment metadata。Mitigation：Task 29 加入 threat model/audit/retention，並在上線前驗證 channel overwrites 與 manager identity provider。
- 高：Checkpoint、handoff、idempotency 尚非 durable atomic operation。Mitigation：Task 26 設計 temp-file + atomic rename/local manifest，Task 32 定義 durable store/outbox 與 crash recovery。
- 中：Attachment-only message 與現有 CaseMessage body contract 不相容。Mitigation：Task 26 先對 fixture 保持 fail closed，再以 ADR/contract version 選擇不失真的表示。
- 中：Live Discord REST adapter、rate-limit handling、manager auth transport 仍是 mock。Mitigation：Task 32 定義 transport/retry/audit，上線前用 fixture contract tests 驗證 adapter。
- 無阻擋 Task 24 本機實作的問題。

## Questions for ChatGPT discussion

- `/dump`/`/follow` 長期應保持 local authenticated admin API/CLI，還是要在新 ADR 後改由 Course Assistant 提供 staff-only Discord interaction？
- Attachment-only Discord message 應以 CaseMessage contract v2 允許空 body，或以明確 machine-generated body 呈現？
- Durable checkpoint/handoff 應使用 SQLite transaction、filesystem atomic manifest，或未來的 backend database/outbox？
- Unknown Discord author 應永遠 fail closed，或允許受審核的 pseudonymous quarantine record？

## Recommended next action

執行 Task 24：在 Course Assistant 新增 anonymous modal reply skeleton。該功能是 writer-owned interaction，需沿用 Task 21/22 的 identity separation、operation id、hook registry 與 fixture writer，並保持 Task 23 reader 無寫入能力。

## Copy-paste handoff

Task 23 已完成 least-privilege Archive Reader skeleton。實作了 health、manager allowlist、案件編號→thread ID、guild/channel allowlist、多頁讀取、最多 100 頁防護、本機 `/dump` 與 `/follow`、last exported Discord message ID checkpoint、CaseMessage contract mapping、attachment metadata-only 交付、local sink 與 request idempotency。`/follow` 只在每次明確呼叫時讀取一次，無 timer/Gateway/background polling；Private Support、未授權、跨 guild/channel、未知 author 均 fail closed。Attachment URL 不進入交付，reader 無 send/role/nickname/status/Discord command tree。完整檢查為 Portal 25/25、GAS 44/44、Pytest 70/70，secret scan 309/0，strict mypy 41 files、Astro 41 files 零診斷，Portal 14 頁與 GAS bundle 建置成功。尚未連 live Discord REST、durable storage/transaction、manager identity provider；attachment-only message 和 CaseMessage 非空 body 也尚需決策。沿用 Task 20，`/dump`/`/follow` 目前是 local/admin interface 而非 Discord slash command。建議下一步執行 Task 24 anonymous modal reply skeleton。
