# Runtime source migration

## Canonical boundary

`runtime/discord-course-bots/` 是 2026-08-10 起受 Git 管理的可重建 runtime source。
原 `.local/discord-course-bots-runtime/` 保持目前 LaunchAgent 的 live working copy，直到獨立
cutover gate；它的 `.env`、virtualenv、SQLite、exports、logs、PID 與 provisioning mapping
不會被搬入 Git。

## Initial mapping

| Local live-tested source | Tracked destination | Initial treatment |
|---|---|---|
| `src/discord_course_bots/` | `src/discord_course_bots/` | byte-for-byte copy |
| `tests/` | `tests/` | byte-for-byte copy, cache excluded |
| `docs/` | `docs/` | copied, then maintained here |
| `.env.example` | `.env.example` | placeholder values only |
| dependency lists | `pyproject.toml` | consolidated as an installable package |

## Explicitly excluded

- `.env` and tokens
- `.venv` and caches
- `data/` and live SQLite
- `exports/`, attachments and manifests
- `runtime/` logs and stale PID files
- provisioning artifacts and real Discord resource mappings

The live launchers have not been switched. A later cutover must compare the tracked package with the
running source, create a backup, stop one service at a time, start from the tracked environment and
verify health before removing the old working copy.
