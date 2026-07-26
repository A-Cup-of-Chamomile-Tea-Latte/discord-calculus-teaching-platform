# 下一階段安全工作包 07–11 報告

日期：2026-07-23  
範圍：Working/Archive Data Model、`dump_bot`、Synthetic Students、GAS/GSheet mock spike、Provisioning dry-run scaffold。

## 完成內容

- 建立 working/archive contracts 與 GAS sheet schema v1.2.0；Users、Consent、既有
  ExportManifest contract 重用，CaseProjection 由 reduced projection 線維護。
- Working 與 archive 分離；支援增量 change version、projection cache、queue、sync cursor、
  weekly dry-run、rollover、archive index、run/change idempotency 與 quota hook。
- `dump_bot` 成為 canonical 名稱，`archive_reader` 保留相容 import/migration note；新增
  structure-only inventory、selected fetch alias、`/dump`、`/follow`、reconciliation 與 manifest。
- 新增完全離線 student／TA／teacher／webhook-like actor、fake interaction、thread lifecycle、
  read/close/reopen/new-activity events，並記錄真人測試限制。
- 新增 declarative provisioning parser/validator/diff/printer/rollback，只有 fixture state，沒有
  apply、SDK、HTTP 或 credential surface。

## 新增 contracts

`active-case`、`sync-state`、`changed-case-queue`、`archive-index`、`sanitized-package`、
`weekly-maintenance-run`、`discord-structure-inventory`。CaseProjection 引用同工作包的
`reduced-case-projection`；Users、Consent、ExportManifest 沿用既有 contracts。

## 安全與可逆假設

- 所有新資料與 actors 使用 `fixture_`／`synthetic_` 標記；未連 Discord/Google、未部署、
  未建立 spreadsheet、未寄信、未讀真實訊息。
- `dump_bot` 僅明確指令讀取，`/follow` 是一次性 checkpoint fetch，沒有 continuous polling。
- rollover 只接受 reviewed plan 中的 closed case；週別、TTL、batch size、schedule 均可替換。
- provisioning `DELETE` 僅是 diff/rollback 描述，不會執行；正式 roles、Private Support、
  identity 與 permissions 未被本輪決定。

## 尚未完成與風險

- 沒有 production Spreadsheet/GAS adapter、locking/outbox、quota telemetry、retention/restore。
- 沒有 live Discord structure/thread adapter、Gateway、token、durable checkpoint 或真人 permission test。
- Synthetic actor 不能驗證 OAuth、DM、Discord UI、real overwrite/rate-limit/event ordering。
- 正式 server plan、角色、班級、Private Support 與 bot permissions 必須經人工討論。

## Diagnostics

- Directed Python：56 passed。
- GAS Vitest：48 passed；TypeScript typecheck passed。
- Portal GAS adapter compatibility：8 passed。
- Ruff：passed；mypy strict directed set：passed（11 source files）。
- root 整合線仍會執行全專案 checks；本線沒有部署或 live service diagnostics。
