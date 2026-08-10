# Discord Infrastructure Provisioning Report

Date: 2026-07-30

Target: allowlisted empty Discord test Guild

Status: **COMPLETE — live verify green; idempotent replay confirmed**

## Main changes

- Added the single live provisioning implementation:
  `tools/discord_provisioning/live.py` and `live_spec.py`.
- Replaced the fixture-only module entrypoint and README with the live CLI.
- Removed the obsolete planner, NAP simulator, provisioning fixtures and their tests.
- Updated the active bot runtime for three managed forums and removed `/lab bootstrap`.
- Updated `docs/IMPLEMENTATION_STATUS.md` and `docs/NEXT_STEPS.md`.

## Commands executed

```bash
python -m tools.discord_provisioning inventory --guild-id <TEST_GUILD_ID>
python -m tools.discord_provisioning apply --guild-id <TEST_GUILD_ID> --reset-lab
python -m tools.discord_provisioning verify --guild-id <TEST_GUILD_ID>
```

The bot services were paused during token use and then restored with their existing LaunchAgents.

## Final managed channel tree

```text
資訊 / Information
├── welcome
├── 公告-announcements
├── 課程資源-course-resources
└── 常見問答-faq

課程問題 / Question
├── 數學問題-math-questions
├── 課務與系統-coursework-systems
└── 其他問題-other-questions

一般交流 / Community
├── 中文聊天
├── english-chat
└── 錯誤回報-error-report

隱密案件 / Private Support
└── [no persistent case channel]

語音與視訊 / Voice Chat
├── Office Hours
└── Study Room

教學團隊 / Staff
├── staff-chat
├── bot-control
└── system-log
```

Discord normalizes `/` and spaces in non-category channel names, so bilingual Forum names use
hyphens. The category display names retain the requested bilingual form.

## Roles

Final hierarchy:

```text
Admin > Staff / TA > DC-Calculus-Manager
      > Verified Member > Guest > DC-Calculus-Archive
```

`Staff / TA` has Manage Messages and voice-member moderation. The current Guild owner is
unrestricted; advisory only: add the same bits to the `Admin` role before assigning it to a
non-owner.

## Created and deleted resources

Created:

- 4 mutable roles, 6 categories, all 15 requested child channels.
- One fixed welcome message.
- One `伺服器使用總則 / Server Guidelines` Forum post.

Deleted:

- `BOT LAB`, old test `PRIVATE SUPPORT`, their test channels and four bootstrap roles.
- Lab-linked local drafts, cases and Private Support test records.
- Approved old default categories `資訊`, `文字頻道`, `語音頻道` and their nine child channels.
- Obsolete fixture-only provisioning code, fixtures and tests.

No bot application/member, dump archive, source knowledge or private export was deleted.

## Mapping and artifacts

- Resource mapping:
  `.local/discord-course-bots-runtime/data/discord_provisioning_resources.json`
- Detailed inventories, operation logs and verify results:
  `.local/discord-course-bots-runtime/artifacts/provisioning/`

These local artifacts are permission-restricted and excluded from Git.

## Verification

- Welcome and guidelines seed content: created and mapped.
- Currently active managed channels: permission scan passed.
- `dump_bot`: read-only or hidden on active managed channels.
- `course_assistant`: no Administrator, Manage Guild, Kick, Ban or Manage Webhooks.
- Cxx roles/channels: absent.
- Live verify: **0 errors, 0 warnings**.
- Second completed apply after full provisioning: **0 mutations**.
- Root Python suite: **164 passed**.
- Runtime bot suite: **25 passed**; 28 known Python 3.14 pytest-asyncio warnings.
- Ruff, `git diff --check` and secret scan: passed.

Both bots were restored and confirmed online after provisioning.

## Timing

| Node | Local time | Duration |
| --- | --- | ---: |
| Runtime/status inspection and bot pause | 19:23–19:24 | ~1 min |
| Live CLI/spec implementation and static tests | 19:24–19:34 | ~10 min |
| Approved Lab/private cleanup and role creation | 19:34 | ~5 sec |
| Permission/API recovery and progressive apply | 19:34–19:51 | ~17 min |
| Approved old default-channel deletion | 19:43 | ~5 sec |
| Seed content, verify and idempotent replay | 19:51–19:54 | ~3 min |
| Final inventory, bot restart and report | 19:54–20:03 | ~9 min |
| Total elapsed | 19:23–20:03 | ~40 min |
| Owner-permission continuation and final green verify | 20:16–20:19 | ~3 min |
