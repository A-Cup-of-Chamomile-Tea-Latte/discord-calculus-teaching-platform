# Fixture data dictionary

## 共同情境

`case_000421` / `C01-7K4M2Q-0702-1000` 是所有 lane 的共同 happy path：Portal 用 CaseLookupResponse 顯示狀態；GAS mock seed Cases worksheet；bots 以 thread `223456789012345678` 取得四則訊息；tools 產生 `export_case_000421_dump`。所有引用都指向同一份 `fixtures/cases/cases.json` case record。

## Record sets

| 檔案                                  | 數量 | 用途                                                                                                            |
| ------------------------------------- | ---: | --------------------------------------------------------------------------------------------------------------- |
| `users/users.json`                    |    4 | 三名虛構學生與一名虛構教學人員                                                                                  |
| `users/verified-emails.json`          |    5 | 全部使用 `example.com`；Amber 同時有分開驗證的 institutional 與偏好 contact email                               |
| `users/discord-accounts.json`         |    4 | 人工配置的 Discord snowflake 字串，不對應真實帳號                                                               |
| `users/course-memberships.json`       |    3 | 班別 `01` 與 `02`，驗證 `nnmmm` course alias                                                                    |
| `users/consents.json`                 |    4 | 帳號分析預設與 Amber 的逐篇排除 override                                                                        |
| `users/activation-codes.json`         |    4 | `UNUSED`、`USED`、`EXPIRED`、`REVOKED`；只含 verifier、綁定與 request fingerprints，另帶明確 permission profile |
| `cases/cases.json`                    |    6 | 五種一般案件狀態，加一個分析排除的 Private Support                                                              |
| `messages/case-000421-thread.json`    |    4 | 父子回覆、編輯、附件 metadata 及混合 `INHERIT/INCLUDED/EXCLUDED`                                                |
| `exports/export-manifests.json`       |    2 | 一般案件 dump 與 Private Support audit-only、分析排除 manifest                                                  |
| `adapters/case-lookup-responses.json` |    2 | `FOUND` 與 `NOT_FOUND` 公開查詢回應                                                                             |

## 重要 ID 與標籤

- `usr_*`、`case_*`、`msg_*` 是 opaque 關聯 ID。
- `C01-7K4M2Q-0702-1000` 等是可讀 case label，不作資料庫主鍵；`-P` 僅表示 Private Support，仍不可公開查詢。
- `01007`、`01008`、`02003` 是 `classCode + joiningOrder(3 digits)` 的 course alias。
- Discord IDs 為 18 位人工數字，只測試「以字串保存」，不代表真實 platform object。
- `sha256:` verifier、binding、request fingerprints 與 64 位檔案 hash 都是重複字元測試值，不是由秘密、真人識別資料或真實檔案產生。

## 隱私情境

- Amber 的 institutional 與 contact records 是兩次獨立驗證；fixture 不把信箱控制權解讀為選課證明。
- `case_000422` 是對一般成員完全匿名顯示、但內部仍有授權管理用途 user ID 的一般案件。
- `case_private_001` 是獨立 Private Support：具有受保護的 `-P` 案號、`TEACHING_STAFF`、`EXCLUDED`，但不出現在一般 case lookup scenarios；`-P` 不授予存取權，也不得用來推測案件存在。
- `msg_000421_c` 有逐篇 `EXCLUDED` 且已編輯，並附只有 metadata 的虛構圖片。
- 所有內容刻意使用簡短虛構描述，不重製真實課程題目、作業或學生對話。

## Mock adapters

`adapters/mock-adapters.json` 以語言中立方式固定五種操作：case lookup、Discord thread fetch、Sheets seed、email delivery、activation-code validation。它只描述輸入／輸出與 fixture path，不會連網、寫 Sheet、寄信、兌換 nonce 或操作 Discord。
