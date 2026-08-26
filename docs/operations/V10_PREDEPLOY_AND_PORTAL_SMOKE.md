# v10 predeploy and Portal smoke runbook

本文件只涵蓋 v10 上線前 gate 與同站 Portal API smoke。它不變更 CNAME、hosting、rollout
或 production deployment。

## Canonical data path

- Course Assistant、Dump Bot 與 Portal API 使用同一個 production `DATABASE_PATH`。
- Bot 與 API 都必須經 `Repository` 交易存取 SQLite；瀏覽器永遠不直接開啟或查詢 DB。
- Portal API 只回傳 reduced case projection，不回傳正文、Email、Discord user ID 或 internal ID。
- SQLite 使用 WAL、foreign keys 與 5 秒 busy timeout；不得把 DB 複製到網站目錄當第二份權威資料。

## Gate 1: production v6 consistent backup

由 production DB owner 在主機上使用 release 內的 rehearsal script。這一步只讀 source，並在獨立
copy 上驗證 backup、restore、migration 與 rollback：

```sh
python3 ops/scripts/sqlite-recovery-rehearsal.py \
  --expected-source-schema 6 \
  --expected-target-schema 13 \
  /absolute/path/to/production.sqlite3 \
  /absolute/path/to/owner-only-work-directory
```

必須回傳 `"status":"PASS"`，且 source file hash 在執行前後相同。不要把 backup、manifest、
Discord token 或 DB path 貼到公開頻道。

## Gate 2: secure Discord mapping preview

Provisioning spec 會建立零權限 identity roles `C01` 到 `C16`，並寫入：

- `course_role_id` -> `Verified Member`
- `visitor_role_id` -> `Guest`
- `ta_role_id`、`professor_role_id` -> `Staff / TA`
- `class_role_01` ... `class_role_16` -> 同名 class role

`system_admin_role_id` 不由 broad `Admin` role 自動推導；system admin 仍以 owner ID 或明示
`/join-admin grant ... system_admin:true` 授權。先執行 provisioning preview/verify，確認 Course
Manager role 高於 16 個 class roles，再決定是否 apply。

## Gate 3: one explicit deploy decision

Gate 1 與 Gate 2 的 receipts 都通過後，由 owner 明示一次 `DEPLOY v10` 或 `DO NOT DEPLOY`。
沒有這句明示授權就停止，不更新 service、不 migrate production DB。

## Post-deploy white-account and Portal smoke

Bot v10 active 後才執行：

1. 白帳號走 Student email start -> 六位數驗證 -> join submission -> reviewer bind/approve。
2. 驗證只收到一次 Email，Course Manager 套用 `Verified Member` 與唯一 `Cxx` role。
3. Guest 白帳號建立公開案，確認案號為 `Guest-{token}-{MMDD}-{HHmm}`、標題為
   `[Guest][主標籤] 原標題`。
4. 一般案與 Private 案各做一次 same-origin `/api/cases/lookup`，確認只回 reduced projection。
5. 確認 API process 與 Bot 使用同一個 `DATABASE_PATH`，並對 Portal audit DB 做 metadata-only
   查核。
6. Private 測試案用縮短 fixture timer 驗證 IDLE -> AUTO_CLOSED -> dump VERIFIED -> channel
   deleted；dump 失敗 fixture 必須保留頻道並出現在 `/ops attention-list`。

數學系網站反向代理與同站 session provider 可在明日測試時接入上述 API；本 runbook 不執行
DNS、CNAME 或 hosting mutation。
