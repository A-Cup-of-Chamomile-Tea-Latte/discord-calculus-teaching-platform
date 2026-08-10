# Bot 最小權限

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 權限均為提案，沒有 live adapter 或套用入口。

## `course_assistant`

- 權限：VIEW_CHANNEL, SEND_MESSAGES, SEND_MESSAGES_IN_THREADS, CREATE_PUBLIC_THREADS, READ_MESSAGE_HISTORY, EMBED_LINKS, ATTACH_FILES, MANAGE_THREADS, MANAGE_NICKNAMES, MANAGE_ROLES, MANAGE_CHANNELS, USE_APPLICATION_COMMANDS
- 限定區域：questions, resources, community, private_support, system

## `dump_bot`

- 權限：VIEW_CHANNEL, READ_MESSAGE_HISTORY, SEND_MESSAGES, ATTACH_FILES, MANAGE_CHANNELS
- 限定區域：questions, resources, private_support, system

共同禁止：`ADMINISTRATOR`、Kick、Ban，以及不受範圍限制的管理能力。
