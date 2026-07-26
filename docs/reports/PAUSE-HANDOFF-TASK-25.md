# Pause handoff after Task 25

## Resume point

- Completed individual tasks: 02–25.
- Completed batch summaries: A, B, C, D.
- Do not redo completed tasks.
- Next task: CODEX_TASKS/26_LOCAL_EXPORT_PIPELINE.md, then Batch E Tasks 27–28 and Batch F Tasks 29–33.

## Archive contents

The handoff archive contains source, fixtures, contracts, task instructions, reports, lockfiles and configuration examples. It intentionally excludes:

- .git metadata;
- node_modules;
- Portal/GAS dist and Astro generated state;
- Python/pytest/mypy/ruff caches;
- macOS metadata;
- local .env files, tokens and credentials.

Dependencies are not vendored. Reinstall them in the new environment.

## New-environment setup

Required baseline:

- Node.js 24.x and npm 11.x;
- Python 3.12–3.14;
- a shell that safely handles spaces and Traditional Chinese paths.

From the extracted project root:

1. Run npm ci.
2. Create a local virtual environment: python3 -m venv .venv.
3. Activate it and run python -m pip install -e '.[dev]'.
4. Run npm run check.
5. Optionally run npm run build.
6. Read PROJECT_DEFAULTS.md, CODEX_TASKS/01_SHARED_CONTEXT.md, this handoff, TASK-25-REPORT.md and BATCH-D_BOTS-SUMMARY.md.
7. Start Task 26 only after the baseline check passes.

The secret scanner keeps its Git-aware candidate scan inside a worktree and automatically uses a bounded filesystem fallback in an extracted archive without `.git`. The fallback excludes dependencies, generated outputs, caches, local exports/data, local `.env` files, binary archives and macOS metadata.

## Last verified state before packaging

- Portal Vitest 25/25.
- GAS Vitest 44/44.
- Pytest 86/86 with 2 known upstream discord.py/Python 3.14 deprecation warnings.
- Strict mypy 46 source files.
- Astro 41 files / 0 diagnostics.
- Portal build 14 pages; GAS bundle built.
- Task 25 report was added after the full check; a final secret/static check is run immediately before packaging.

## Safety boundaries to retain

- Fixture/local data only; never use real student data or real secrets.
- No push, deploy, email, cloud resource or Discord connection without explicit approval.
- Private Support remains BACKEND_ONLY and excluded from public lookup, analysis and content export.
- Archive Reader performs explicit selected-thread reads only; no background polling.
- Anonymous reply uses modal/bot repost only; never post-then-delete.
- Course Assistant and Archive Reader keep separate tokens and narrow writer/reader capabilities.
- Do not treat NTU email control or Discord OAuth as course enrollment proof.

## Working-tree note

Task 25A confirmed that the original inner project did contain `.git`; it has been preserved and moved with the repository to the canonical project root. Its `main` branch is unborn and has no commits or remotes, so there is Git metadata but no commit history capable of reconstructing omitted work. The handoff archive still intentionally excludes `.git` and remains a portable artifact.

The canonical root is now:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

GPT/Codex exchange documents and prior instruction/handoff ZIPs are stored under `project-exchange/`.
