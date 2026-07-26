# Bot service interfaces

這些是 framework-neutral boundaries；Task 21 已將其落成 Python protocols/data classes。Service 不接觸 environment token，Discord-specific adapter 不決定產品授權。

## Command/value objects

所有 commands 都包含 `operation_id`、`requested_by_user_id`、`requested_at` 與最小 payload。Discord snowflake 以字串保存。內容、visibility、author display、analysis permission維持獨立欄位。

```text
PublishQuestion(operation_id, case_id, title, body, visibility, author_display_mode)
PostAnonymousReply(operation_id, case_id, body, parent_message_id?)
ChangeCaseStatus(operation_id, case_id, expected_status, new_status)
ApplyMembership(operation_id, user_id, guild_id, course_alias, allowed_role_ids)
CreatePrivateSupport(operation_id, case_id, body)
FetchSelectedThread(request_id, case_id, channel_id, thread_id, cursor?)
```

## Application services

```text
CourseAssistantService.publish_website_question(command) -> PublishedCase
CourseAssistantService.post_anonymous_reply(command) -> PublishedMessage
CourseAssistantService.change_case_status(command) -> CaseStatusResult
CourseAssistantService.apply_membership(command) -> MembershipApplyResult
CourseAssistantService.create_private_support(command) -> PrivateSupportResult

ArchiveReaderService.fetch_selected_thread(request) -> ThreadSnapshot  # `dump_bot` compatibility service name
```

`ModerationService` 在 v1 沒有 method；新增任何 method 需要 ADR。Local export rendering/persistence 不屬於 `ArchiveReaderService`（canonical product name: `dump_bot`），由 Task 26 工具接收 `ThreadSnapshot` 後處理。

## Required ports

| Port                  | Consumer                  | Responsibility                                                     | Forbidden behavior                                  |
| --------------------- | ------------------------- | ------------------------------------------------------------------ | --------------------------------------------------- |
| `DiscordCourseWriter` | course_assistant          | create approved forum/thread posts, replies, role/nickname changes | arbitrary channel/role IDs, history export          |
| `DiscordThreadReader` | dump_bot            | fetch one allowlisted thread and message pages                     | send/edit/delete/role/nickname methods              |
| `CaseRepository`      | course_assistant          | compare-and-set status and Discord mapping                         | expose raw Sheet rows to handler                    |
| `MembershipAuthority` | course_assistant          | return an already-approved membership decision                     | infer enrollment from Discord/email alone           |
| `IdempotencyStore`    | both, separate namespaces | begin/complete/fail an operation once                              | process-local guarantee in production               |
| `AuditSink`           | both                      | allowlisted metadata/outcome                                       | tokens, raw request bodies, Private Support content |
| `Clock`               | both                      | deterministic timestamps                                           | hidden wall-clock calls in domain tests             |

The writer and reader protocols intentionally have no common “DiscordClient with every method” super-interface. A concrete single-process adapter may implement both protocols, but dependency injection exposes only the narrow port each service accepts.

## Error contract

Services return typed outcomes such as `COMPLETED`, `ALREADY_COMPLETED`, `NOT_AUTHORIZED`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `PROVIDER_UNAVAILABLE`, and `NOT_CONFIGURED`. Exceptions are reserved for programming/configuration faults. Public handlers project internal outcomes into generic, non-enumerating responses where privacy requires it.

No retry changes `operation_id`. A provider timeout is ambiguous until reconciliation proves whether the Discord side effect happened; services must not blindly issue a second write.
