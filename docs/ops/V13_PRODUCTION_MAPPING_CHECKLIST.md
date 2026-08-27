# v13 Deployment Mapping Checklist

狀態：`DISCORD_LIVE_VERIFIED / SECURE_VALUES_CAPTURED / HOST_BOOTSTRAP_PENDING`。真實 Discord resource IDs 只保存在 mode `0600` 的 ignored secure mapping；本表與 Git 不保存或顯示值。

## 已可由 repository 證明

| 項目 | repository 結論 | 來源 |
| --- | --- | --- |
| Term | `115-1` | `config/academic/115-1/course-operations.yaml` |
| Class → Module | C01–C04→M1；C05–C09→M2；C10–C13→M3；C14–C16→M4 | canonical term spec，狀態 `APPROVED` |
| Module role | 不建立；Module 是 backend attribute | academic spec |
| Managed forums | math questions、coursework／systems、other problem／free talk | `config/proposed/server.yaml` 與 live spec 的 logical intent |
| Private category | `private_support` logical key | proposed server config |
| Reviewer levels | `REVIEWER`、`SYSTEM_ADMIN` | runtime migration／repository |

## Production gate 現況

| Gate | 目前狀態 | 需要提供／驗證 |
| --- | --- | --- |
| Guild | Live allowlisted Guild 已唯讀盤點 | Guild ID 已安全保存，不在 receipt／聊天列印；production identity 仍由 owner 的 host/runtime 邊界確認 |
| Course role | PASS | canonical role 是 `verified_member`／`Verified Member`；`registered_audit` 已排除為 database-only attribute |
| Visitor role | PASS | `guest`／`Guest` 已解析並安全保存 |
| C01–C16 class roles | PASS | 16 個零權限 identity roles 已建立，exact coverage verify PASS |
| C01–C16 role hierarchy | PASS | Course Manager 可管理 class roles；完整 live verify 為 0 error／0 warning |
| Managed forums | PASS | 三個 forum logical keys、parent、type、Course Manager／Archive bot boundary 已由 live verify 核對 |
| Private Support category | PASS | `category.private_support` 與 ACL policy 已由 live verify 核對 |
| Reviewer bootstrap | 待 host 一次確認 | v6 尚無 `reviewer_grants` table；predeploy 只確認 secure `BOT_OWNER_IDS` 非空，不輸出值 |
| Reviewer／System admin grants | Post-deploy gate | v13 migration 後由 bootstrap owner 用 `/join-admin grant` 建立 explicit user grants；UI `staff` 不等於 production authorization |
| Runtime config | Post-deploy apply／smoke | 由 owner commands 寫入 role／forum／category／class→Module，再以白帳號驗證，不把 ID 寫入 Git |

## C01–C16 class→Module 收據（可先核對，不填 Discord ID）

| Class | Module | Class role ID |
| --- | --- | --- |
| C01 | M1 | secure mapping 已保存 |
| C02 | M1 | secure mapping 已保存 |
| C03 | M1 | secure mapping 已保存 |
| C04 | M1 | secure mapping 已保存 |
| C05 | M2 | secure mapping 已保存 |
| C06 | M2 | secure mapping 已保存 |
| C07 | M2 | secure mapping 已保存 |
| C08 | M2 | secure mapping 已保存 |
| C09 | M2 | secure mapping 已保存 |
| C10 | M3 | secure mapping 已保存 |
| C11 | M3 | secure mapping 已保存 |
| C12 | M3 | secure mapping 已保存 |
| C13 | M3 | secure mapping 已保存 |
| C14 | M4 | secure mapping 已保存 |
| C15 | M4 | secure mapping 已保存 |
| C16 | M4 | secure mapping 已保存 |

## 驗證方式

1. 先執行 `python3 ops/scripts/validate-v13-mapping.py config/release/v13-production-mapping.template.json --allow-pending`，確認 class coverage 與 class→Module 不漂移。
2. 對 mode `0600` secure mapping 重跑 validator；canonical keys、17–20 位 snowflake、resource ID uniqueness 與 bootstrap/grant gate 必須通過，且輸出不得包含 IDs。
3. Guild membership／名稱／ACL 由 live inventory-backed verify 負責；純 shape validator 不冒充能判斷錯誤 Guild。
4. 部署後以 Student／Guest／Staff 與兩個 bot 的白帳號矩陣驗證 view／post／manage 邊界。

目前唯一未完成的 predeploy mapping 項目是 production host 的 `BOT_OWNER_IDS` 非空確認；explicit reviewer grants 是 migration 後、rollout 前 gate。

## Post-v13 additive Private 入口

永久入口 `channel.private_support_entry` 不屬於 frozen v13 deployment mapping，也不改寫 v13 release evidence。它只使用 provisioning resource map 與 SQLite `private_support_entry_channel_id` 保存 live ID。

套用時先跑 `plan-private-entry`，確認只建立／採用 `開啟隱密案件-open-private-case`、設定雙語 topic 與 ACL，再跑 `ensure-private-entry`。舊名 `開啟隱密案件` 只作一次性原地改名 alias；其他 drift 只回報、不修復。既有 Private category 與所有動態案件頻道都必須保留。若 operation log 證明入口是本次新建才可刪除；adopted 入口只能依 before inventory 還原。
