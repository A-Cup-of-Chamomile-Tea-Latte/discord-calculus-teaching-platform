# GPT → Codex Exchange：Task 25 後整理與 Task 26 續作

請先閱讀：

- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- `docs/reports/TASK-25-REPORT.md`
- `docs/reports/BATCH-D_BOTS-SUMMARY.md`
- `docs/reports/PAUSE-HANDOFF-TASK-25.md`
- 本文件
- `Task25_GPT_Independent_Review_v2_2026-07-19.md`

## 目標

不要重做 Tasks 02–25。先完成一次低風險的 repository relocation／handoff hardening，通過完整驗證後，再依既有 `CODEX_TASKS/26_LOCAL_EXPORT_PIPELINE.md` 開始 Task 26。

不得 push、deploy、寄信、連接真實 Discord server、使用真實學生資料或要求 production secrets。

---

## A. 先確認現有 Git repository，不可盲目初始化

專案負責人記得本機已有 Git repository，只是 `.git` 沒有被放進 handoff ZIP。

請在目前實際工作目錄中先確認：

- Git top-level path。
- `git status`。
- 最近 commit history。
- `.git` 實際位於外層還是內層。

規則：

1. 若 `.git` 已存在，必須保留既有歷史，不可重新 `git init`。
2. 不可建立 nested Git repository。
3. 只有確認完全沒有 Git metadata 時，才可提出初始化建議；不要默默建立。
4. 若 pause handoff 中「沒有 established commit history」與實況不符，請修正文檔。

---

## B. 將 repository 上移成唯一 project root

Canonical root：

```text
/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案
```

目前可能是：

```text
.../Discord_微積分模組教學優化專案/
    Discord 微積分模組教學優化專案/
```

期望結果：

```text
Discord 微積分模組教學優化專案/
├── .git/
├── apps/
├── bots/
├── tools/
├── contracts/
├── fixtures/
├── tests/
├── docs/
├── CODEX_TASKS/
├── project-exchange/
└── ...
```

請採安全做法：

1. 先列出外層與內層內容，辨認 actual repository 與 exchange files。
2. 在外層建立 `project-exchange/`。
3. 將原外層的 GPT／Codex 交換文件、審核報告、指令 ZIP、handoff ZIP 等移入 `project-exchange/`。
4. 將 actual repository 的所有內容上移一層，包括 hidden files 與既有 `.git`。
5. 不覆寫同名檔案；遇到 collision 應停下並在報告中列出。
6. 移動後確認：
   - `git rev-parse --show-toplevel` 指向 canonical root；
   - `git status` 合理；
   - 沒有殘留同名 nested project root；
   - file counts 與關鍵目錄完整。
7. 更新文件內仍指向舊雙層路徑的絕對路徑。

不要改 repository 的遠端設定，也不要 push。

---

## C. 修正 handoff portability

目前 handoff ZIP 排除 `.git`，但 secret scanner 依賴 `git ls-files`，使 freshly extracted archive 的 `npm run check` 可能失敗。

請完成：

1. 在 Git worktree 中維持現有 tracked-files scan。
2. 在沒有 `.git` 的解壓目錄提供安全 filesystem fallback。
3. fallback 必須排除：
   - `.git`
   - `.venv`
   - `node_modules`
   - build outputs
   - caches
   - `.env`
   - binary archives
   - macOS metadata
4. 新增 regression test，證明無 `.git` 的 handoff copy 可以執行 secret scan。
5. 更新 `docs/reports/PAUSE-HANDOFF-TASK-25.md` 的新環境說明。

若此修改會大幅擴張範圍，先實作最小且可測試的修正，不要重寫整套 quality tooling。

---

## D. 記錄但不要現在修正 GitHub Pages access-scope issue

在 `docs/decisions/UNRESOLVED.md` 新增一項未決事項，內容必須包含：

- GitHub Pages 是 internet-public。
- 產品中的 course-wide public 是課程成員可見，不等於全網公開。
- fixtures／prototype 目前可保留 prebuilt case pages 與 fixture case list。
- production 不可直接假設沿用。
- 在 Task 33 完成後進行整體 review，再決定：
  - course-session access gate；
  - production list-all-cases route；
  - one-case-at-a-time lookup；
  - 未登入可見欄位。

此輪只記錄，不修改 Portal、GAS routes、fixtures 或案件頁行為。

---

## E. Private Support 保持 Task 25 現況

專案負責人目前有其他產品設計想法，因此：

- 不調整 Task 25 participant allowlist。
- 不改 triage／escalation 行為。
- 不改 Private Support reference／tracking 產品流程。
- 不重做 Task 25。
- 可將相關事項保留在未決清單，但不得自行選定新 policy。

Task 26 仍須遵守既有安全邊界：Private Support 預設排除於一般 teaching-analysis content export。

---

## F. 驗證與報告

Repository relocation／hardening 完成後，執行完整既有檢查與 build。

新增：

```text
docs/reports/TASK-25A-RELOCATION-HARDENING-REPORT.md
```

報告需包含：

1. 原始目錄結構。
2. 最終目錄結構。
3. Git repository 實際狀態與既有 history 是否存在。
4. 搬移及文件修改清單。
5. secret scanner fallback 的實作方式。
6. 新增測試及結果。
7. 完整 tests／lint／typecheck／build 結果。
8. 未解決問題。
9. 可直接貼回 ChatGPT 的繁體中文摘要。

確認全部通過後：

- 開始 `CODEX_TASKS/26_LOCAL_EXPORT_PIPELINE.md`。
- 完成 Task 26 原定 acceptance criteria 與報告。
- 不提前執行 Task 27，除非專案負責人另有指示。
