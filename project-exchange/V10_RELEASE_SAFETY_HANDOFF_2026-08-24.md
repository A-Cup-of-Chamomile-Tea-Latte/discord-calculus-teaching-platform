---
schema: ai-handoff/v1
from: Codex
from_context: side-v10-release
to: PM
project: Discord 教學優化
topic: v10 Release Safety
purpose: bounded-release-safety-work
status: fail-closed-pending-owner-input
production_deployed: false
---

# v10 Release Safety 交接

## 結論

已完成本輪所有不需部署授權的 release-safety 工作，但不能把 candidate 宣稱為可部署成品：production consistent backup 尚未進入本 workspace，production mapping 仍有 owner 缺值。依固定停止線，production rehearsal 與 deploy decision 維持 `FAIL_CLOSED`；沒有執行 deploy、restart、live migration、Discord／Google／website 修改或 secrets 讀寫。

## 變更

- Branch：`codex/v10-release-safety-20260824`
- Commit：`d40515b` (`docs(ops): prepare v10 release safety gates`)
- 新增／更新：
  - `ops/scripts/sqlite-recovery-rehearsal.py`：可選 strict source schema gate；production 使用 `--expected-source-schema 6`，要求 source／backup／restore integrity、ledger 連續性、row counts、rollback copy equivalence、owner-only mode、writable workspace 與 source checksum 穩定。
  - `ops/scripts/validate-v10-mapping.py`：只輸出 shape、缺值與錯誤欄位，不輸出任何 Discord／使用者 ID。
  - `config/release/v10-production-mapping.template.json`：mapping 形狀與安全 placeholder；未填真實 ID。
  - `docs/ops/V10_PRODUCTION_MAPPING_CHECKLIST.md`：course／visitor role、C01–C16 class roles、class→Module、forum、Private category、reviewer／system admin 的完整清單與缺值。
  - `docs/ops/V10_RELEASE_SAFETY_RUNBOOK.md`：單一路徑 deploy／smoke／rollback，涵蓋三服務、schema、single writer、queues、manual attention、backup retention 與 fail-closed stop conditions。
  - `docs/ops/V10_RELEASE_SAFETY_RECEIPT.json`：目前安全收據，明示 `productionBackupRehearsal=BLOCKED_NO_PRODUCTION_BACKUP_IN_WORKSPACE`、`mapping=PENDING_OWNER_INPUT`、`deployExecuted=false`。

## 驗證收據

- `PYTHONPATH=runtime/discord-course-bots/src .venv/bin/python -m pytest -q runtime/discord-course-bots/tests/test_recovery_tooling.py runtime/discord-course-bots/tests/test_deployment_entrypoint.py`：`8 passed`。
- `PYTHONPATH=runtime/discord-course-bots/src .venv/bin/python -m pytest -q tests/tools/test_academic_term_config.py`：`6 passed`。
- `python3 ops/scripts/validate-v10-mapping.py config/release/v10-production-mapping.template.json --allow-pending`：shape valid、class→Module `PASS`、`25` 個 owner 缺值、狀態 `PENDING_OWNER_INPUT`；未讀／輸出敏感值。
- 以非-production schema-v10 fixture 帶 `--expected-source-schema 6`：strict gate 正確回 `FAIL`，不接受錯誤 source schema。
- `.venv/bin/ruff check ...`、`.venv/bin/ruff format --check ...`、`git diff --check`：全部通過。

## 尚缺且需一次性 owner／PM 請求

1. Host owner 提供 production v6 consistent backup 的 owner-only copy；只把該副本交給 runbook 的隔離 rehearsal，不提供 raw rows 到聊天或 Git。
2. 提供／核准 production mapping：guild、course role 的 canonical 選擇與 ID、visitor role ID、C01–C16 class role IDs、3 個 managed forum IDs、Private Support category ID、secure runtime 的 `REVIEWER`／`SYSTEM_ADMIN` grants。Template validator 目前列出 25 個缺值。
3. 指定 backup retention owner 與接受的保留窗口；未指定前不自動刪除 pre-deploy rollback DB。
4. 上述 gate PASS 後，PM／課程 owner 再另行明示 v10 deploy authorization；目前不建議進入 deploy execution。

## 工作樹注意

工作樹中另有一批既存 Portal／backend 變更（`apps/portal/...`、`runtime/discord-course-bots/src/discord_course_bots/portal_backend.py`），未由本任務修改，也未納入 `d40515b`；請由原 owner 另行處理。
