# BOT_CONFIG — Test Guild v0.1

## Environment variables

| Name | Required by | Purpose |
|---|---|---|
| `COURSE_ASSISTANT_TOKEN` | course_assistant | Bot token; local secret |
| `COURSE_ASSISTANT_CLIENT_ID` | invite generator | OAuth install URL |
| `DUMP_BOT_TOKEN` | dump_bot | Bot token; local secret |
| `DUMP_BOT_CLIENT_ID` | invite generator | OAuth install URL |
| `TEST_GUILD_ID` | both | Hard single-guild guard |
| `BOT_OWNER_IDS` | course_assistant | Destructive lab command allowlist |
| `TEST_MODULE_CODE` | course_assistant | Temporary module prefix, default `M1` |
| `DATABASE_PATH` | course_assistant | SQLite test database |
| `DRAFT_REMINDER_SECONDS` | course_assistant | Draft reminder threshold |
| `DRAFT_DELETE_SECONDS` | course_assistant | Draft deletion threshold |

## Runtime IDs created by `/lab bootstrap`

- `verified_student_role_id`
- `guest_role_id`
- `ta_role_id`
- `professor_role_id`
- `bot_control_channel_id`
- `public_forum_channel_id`
- `private_support_category_id`

These values are stored in SQLite and are the first write-scope allowlist.
