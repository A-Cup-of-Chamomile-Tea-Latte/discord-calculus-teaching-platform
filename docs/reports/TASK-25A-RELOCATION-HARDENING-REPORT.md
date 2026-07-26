# TASK-25A report — repository relocation and handoff hardening

## Outcome

Complete。已把原本多一層的 Git 儲存庫安全搬到指定的 canonical project root，保留原 `.git`，沒有重新 `git init`、沒有 commit/push/remote 變更。外層交接文件已集中到 `project-exchange/`。Secret scanner 在有 Git 時仍使用 Git candidate set，在無 `.git` 的壓縮檔或交接副本中則改用 bounded filesystem fallback；真正無 Git 副本已實測 323 candidates / 0 findings。GitHub Pages 公開性與課程成員可見性的差異已登記為 U-011，留待 Task 33，本任務沒有改 Portal 行為。

## Original structure

- 外層指定目錄：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`。
- 實際 Git root 在內層：`.../Discord_微積分模組教學優化專案/Discord 微積分模組教學優化專案`。
- 內層包含 `.git`、source、tests、dependencies 與 caches；搬移前盤點為 17,492 files、28 symlinks、約 371 MB。
- 外層另有 Codex 任務索引、兩份交接 ZIP、GPT 交接文件與獨立審查文件。除 `.DS_Store` 外沒有路徑衝突。

## Final structure

- Canonical Git root 現為使用者指定的外層目錄：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`。
- `.git`、`apps/`、`bots/`、`contracts/`、`docs/`、`fixtures/`、`tests/` 與 `tools/` 都在 canonical root。
- 原外層交接材料現在 `project-exchange/`；歷史交接文本內的舊路徑作為當時紀錄保留，active docs 無 stale double-root path。
- 多餘內層目錄已移除，沒有 nested `.git`。最後盤點為 18,076 files、28 symlinks，數量差異主要來自重建 `.venv`、build outputs 與新增測試/報告。

## Git state and preservation

- `git rev-parse --show-toplevel` 回傳 canonical root。
- 原 `.git` 直接保留並搬移，未建立新 repository。
- Repository 原本就是 unborn `main`：`git status` 顯示 `No commits yet on main`，`git rev-list --count --all` 為 0，所以沒有可供驗證的 commit history。
- `git remote -v` 無輸出；本任務沒有新增 remote、commit、push、branch 或 tag。
- 搬移後舊 `.venv` shebang 仍指向舊絕對路徑，因此已將舊環境可恢復地移到 `/tmp/codex-task25a-relocated-broken-venv`，並用 Homebrew Python 3.14.6 在 canonical root 重建 `.venv`。

## Moves and documentation changes

- 將內層 project tree 搬到 canonical root，搬移前先盤點 hidden files、symlinks、Git state 與路徑衝突。
- 將外層交接文件搬到 `project-exchange/`，不覆寫原 project files。
- 內層 `.DS_Store` 為唯一衝突，已可恢復地放到 `/tmp/codex-task25a-nested-root.DS_Store`；外層 `.DS_Store` 保留且受 `.gitignore` 排除。
- Task 25A 初次盤點誤將 `PROJECT_DEFAULTS.md` 的空白路徑當成 canonical path；Task 33 獨立稽核發現後，已將 active defaults、使用說明與環境診斷統一更正為實際的底線 root。
- `docs/reports/PAUSE-HANDOFF-TASK-25.md` 已更正 Git 實況、canonical root、exchange location 與 fallback 行為。
- `docs/decisions/UNRESOLVED.md` 新增 U-011，明確把 GitHub Pages access-scope 放到 Task 33 決策。

## Secret scanner hardening

- Git worktree 仍使用 `git ls-files -z --cached --others --exclude-standard`，保留原 candidate semantics。
- Git 不存在或指令失敗時，改用排序過的 filesystem walk，只收錄 regular files，不追蹤 symlink。
- Fallback 排除 `.git`、virtualenv、Node/Python dependencies、cache、coverage、build/dist、local data、exports、`.env` 及 `.env.*`（保留 `.env.example`）、macOS metadata 與常見 archives。
- 新增 regression test，在沒有 `.git` 的 temp tree 中驗證只會收錄 `.env.example` 與正常 source file，不會誤掃 excluded directories、`.env`、ZIP 與 `.DS_Store`。
- 另建立實際無 `.git` 的 handoff copy `/tmp/codex-task25a-handoff-copy-20260719`。Python module path 確認載入該副本內的 scanner，整合掃描結果為 323 candidate files / 0 findings。

## Policy preservation and unresolved issue

- Task 25 Private Support 的 participants、escalation、TEACHING_STAFF visibility、EXCLUDED analysis/content export 與 backend-only default 都未改動。
- U-011 記錄：GitHub Pages 通常是 internet-public static hosting，不能在未驗證時等同於只限課程成員。Fixture 預建案例頁/清單可繼續作教學 prototype，production 不得默認為有 course-session gate。
- Task 33 需決定 course-session gate、production list-all route、single-case lookup 與 unauthenticated fields；本任務未更改 Portal/GAS/fixture behavior。

## Verification

- `npm run check` 通過。
- Secret scan：canonical Git worktree 326 candidates / 0 findings；無 Git handoff copy 323 / 0。
- Formatting/lint：Prettier 通過；Ruff 46 files formatted，Ruff lint 通過。
- Type checks：Astro 41 files / 0 errors / 0 warnings / 0 hints；GAS `tsc` 通過；mypy 46 source files / 0 issues。
- Tests：Portal 25/25、GAS 44/44、Python 87/87 passed。新增的第 87 個 Python test 是 non-Git fallback regression。
- Builds：Portal 14 static pages；GAS `dist/Code.js` 與 `dist/appsscript.json` 產生成功。
- `git diff --check` 通過；canonical root 下無 nested project root 或 nested `.git`。
- 已知警告：Python 3.14 + discord.py 2.7.1 的既有 tests 仍有 2 個 `asyncio.iscoroutinefunction` deprecation warnings，Task 25A 未新增 warning。

## Commands executed

- `git rev-parse`、`git status`、`git remote`、`git rev-list`、`find`、`du`、`rg` 與 collision inventory，用於搬移前後盤點。
- 精確的 `mv`、`rmdir` 與 `rsync --exclude`，用於安全搬移與建立 non-Git integration copy。
- `/opt/homebrew/bin/python3 -m venv .venv` 與 `.venv/bin/python -m pip install -e '.[dev]'`。
- Directed Ruff/mypy/pytest，完整 `npm run check`、`npm run build`、Prettier 與 `git diff --check`。

沒有 Discord login/token/Gateway/REST call、OAuth、production data、email、deploy、Git remote change、commit 或 push。

## Risks and notes

- Repository 仍為 unborn main，全部 project files 都是 untracked；這是原始 Git state，不是搬移導致的 history loss。後續若要建立基線 commit，需由使用者明確授權並先審查內容。
- Fallback exclusions 以降低解壓 handoff 的 noise 與處理量；實際 source tree 如新增另一種 generated directory/archive format，應同步擴充 regression fixtures。
- U-011 在 Task 33 前仍是 production access-control blocker，不影響 Task 26 fixture-only local export pipeline。
- `/tmp` 中的舊 virtualenv、collision `.DS_Store` 與 non-Git copy 是可恢復/可重建的暫存物，本任務沒有刪除使用者原始資料。

## Recommended next action

進入 Task 26 local export pipeline：先定義 fixture/live adapter 邊界與輸出 contracts，再實作 deterministic pagination、checkpoint resume、idempotent atomic files、Markdown reply context 與 attachment index。不連線 Discord，不使用 real credentials/data，不開始 Task 27。

## Copy-paste handoff

Task 25A 已完成 repository relocation/hardening。原本 Git root 在指定專案目錄內多一層的 `Discord 微積分模組教學優化專案/`，現已將原 `.git` 與 project tree 安全搬到 canonical root `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`，外層交接文件集中到 `project-exchange/`，無 nested root/.git。Repository 原本就是 unborn main（0 commits、0 remotes），沒有 init/commit/push/remote change。Secret scanner 保留 Git candidate behavior，新增 bounded non-Git fallback，排除 VCS/dependencies/cache/build/dist/local data/exports/.env/archive/macOS metadata，保留 `.env.example`；unit regression 與真正無 `.git` handoff copy 均通過，後者 323 candidates/0 findings。Task 25 Private Support policy 未改。GitHub Pages public-vs-course-only mismatch 已登記 U-011，留待 Task 33，Portal 行為未改。完整驗證：secret 326/0、Portal 25/25、GAS 44/44、Python 87/87、mypy 46 files、Astro 41 files零診斷、Portal 14 pages 與 GAS bundle build 成功。下一步可開始 Task 26 fixture-only local export pipeline，不連真實 Discord，不開始 Task 27。
