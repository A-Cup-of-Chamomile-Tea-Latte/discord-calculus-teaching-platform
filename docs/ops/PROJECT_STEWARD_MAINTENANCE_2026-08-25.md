# Project Steward maintenance — 2026-08-25

模式：silent walker；只修正會誤導現行操作的 canonical 文件，不改歷史 task reports／ADR，不觸碰
production、secrets、Discord 或 Google。

## Current checkpoint

- Production：Remote Linux 唯一 writer，schema v6，三服務與 24 小時 observation PASS。
- Candidate：schema v10 release `3411aff` 已放入 remote staging，deploy request 為
  `target_schema=10`／`ADDITIVE`；owner 已明示授權。
- Pending：root-owned restricted deployer 更新；完成後才由 `ding` 執行 deployment。任何 staging
  migration、checksum、integrity、fresh health 或 rollback gate 失敗均 fail closed。
- Portal：same-origin join／one-case lookup 已完成本機候選與安全測試；production session／audit／origin
  runtime 與 public rollout 尚未接線。

## Findings resolved in this maintenance branch

1. 將初次 Mac → Remote cutover runbook 標示為歷史文件，避免重跑已完成的 cutover。
2. 對齊 reviewer／TA／student guides：區分本機 backend candidate、public fail-closed 與 production 接線。
3. 修正 OAuth 文件仍聲稱 credential 尚未安裝的過期狀態。
4. 為舊 `UNRESOLVED` checkpoint 加上歷史時間邊界，避免把 Local SQLite 誤認為現行 authority。
5. 更新 implementation／next-steps／v10 runbook，記錄 release staging 與 deploy authorization，不冒充已部署。

## Verification receipt

- Canonical full gate：secret scan 677 files／0 findings；format、lint、typecheck PASS；Portal 61、Config
  Studio 3、GAS 66、Python 297 tests PASS。
- Python 僅有 2 個 `discord.py` 對 Python 3.14 的 deprecation warnings；不是目前 runtime failure，持續追蹤
  Python 3.16 前相容性即可。
- v10 deployer／recovery targeted tests：8 PASS。

## Still open by design

- Production v6 consistent backup-copy rehearsal 尚無獨立 receipt；restricted deployer 仍必須先在
  consistent staging copy 完成 v6 → v10 migration、ledger 與 integrity gate，再允許停服務。
- Production Discord mapping、白帳號 E2E、deployment smoke 與 rollback receipt 要在 v10 cutover 流程完成。
- Incident／privacy／retention owner 的 `[TBD]` 是治理決策，不在 silent-walker 維護中代填。
