# v10 Production Mapping Checklist

狀態：`PENDING_OWNER_INPUT`。本表只核對 logical shape 與缺值；不讀取或保存既有 Discord resource IDs、使用者 IDs 或 secrets，也不代表已套用 Discord。

## 已可由 repository 證明

| 項目 | repository 結論 | 來源 |
| --- | --- | --- |
| Term | `115-1` | `config/academic/115-1/course-operations.yaml` |
| Class → Module | C01–C04→M1；C05–C09→M2；C10–C13→M3；C14–C16→M4 | canonical term spec，狀態 `APPROVED` |
| Module role | 不建立；Module 是 backend attribute | academic spec |
| Managed forums | math questions、coursework／systems、other problem／free talk | `config/proposed/server.yaml` 與 live spec 的 logical intent |
| Private category | `private_support` logical key | proposed server config |
| Reviewer levels | `REVIEWER`、`SYSTEM_ADMIN` | runtime migration／repository |

## 必須由 owner 提供的 production values

| Gate | 目前狀態 | 需要提供／驗證 |
| --- | --- | --- |
| Guild | 缺值 | 唯一 production Guild，確認不是 fixture/test Guild |
| Course role | 未定稿且缺值 | 選定 broad course membership role 的 canonical logical key／name／ID；`verified_member` 與 `registered_audit` 不可自行互換，後者是 database-only attribute |
| Visitor role | 缺值 | `guest` logical key 對應的 production role ID |
| C01–C16 class roles | 全部缺值 | 16 個 allowlisted role IDs；不得把 Module role 或任意同名角色當成 class role |
| C01–C16 role hierarchy | 未驗證 | bot 可管理的 role 位置、staff／administrator 高於 bot、bot 不得擁有 `ADMINISTRATOR` |
| Managed forums | 三個 production channel IDs 缺值 | `forum.math_questions`、`forum.coursework_systems`、`forum.other_problem_free_talk`；確認 parent category、forum type、tags、Course Assistant 可管理且 dump_bot 只讀 |
| Private Support category | 缺值 | `category.private_support` production category ID；`@everyone`、student、guest 不可見，只有 creator／staff／course assistant／dump bot 依核准 policy 可見 |
| Reviewer | 未配置 | 以 secure runtime explicit user grant 設定 `REVIEWER`，不得把 UI `staff` 當成 production authorization |
| System admin | 未配置 | 以 secure runtime explicit user grant 設定 `SYSTEM_ADMIN`，不得在 Git 或聊天寫入 user IDs |
| Runtime config | 未核對 | `managed_forum_ids`、`private_support_category_id`、course／visitor role keys 與 grants 的一致性 |

## C01–C16 class→Module 收據（可先核對，不填 Discord ID）

| Class | Module | Class role ID |
| --- | --- | --- |
| C01 | M1 | 待 owner 提供 |
| C02 | M1 | 待 owner 提供 |
| C03 | M1 | 待 owner 提供 |
| C04 | M1 | 待 owner 提供 |
| C05 | M2 | 待 owner 提供 |
| C06 | M2 | 待 owner 提供 |
| C07 | M2 | 待 owner 提供 |
| C08 | M2 | 待 owner 提供 |
| C09 | M2 | 待 owner 提供 |
| C10 | M3 | 待 owner 提供 |
| C11 | M3 | 待 owner 提供 |
| C12 | M3 | 待 owner 提供 |
| C13 | M3 | 待 owner 提供 |
| C14 | M4 | 待 owner 提供 |
| C15 | M4 | 待 owner 提供 |
| C16 | M4 | 待 owner 提供 |

## 驗證方式

1. 先執行 `python3 ops/scripts/validate-v10-mapping.py config/release/v10-production-mapping.template.json --allow-pending`，確認 class coverage 與 class→Module 不漂移。
2. Owner 以 secure runtime／owner-only mapping 提供值後，重跑同一 validator；未填欄位、非 17–20 位數字 snowflake、重複資源或錯誤 Guild 必須 fail closed。
3. 以 read-only inventory／resolved-member simulation 驗證學生、其他班學生、該班 TA、其他班 TA、staff、guest 與兩個 bot 的 view／post／manage 邊界。
4. 產生 add／modify／remove diff 與 rollback plan，交由 owner 審閱；本任務不執行 Discord apply。

在 secure runtime values 尚未提供前，mapping gate 是 `PENDING_OWNER_INPUT`，不能進入 deploy decision。
