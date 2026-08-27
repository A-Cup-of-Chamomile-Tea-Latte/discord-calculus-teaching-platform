# 案件狀態查詢 QA

更新日期：2026-08-28

案件查詢現在是 one-case-at-a-time 的狀態摘要介面。Reviewer 使用完全虛構 fixture；
預設 public artifact 維持 fail closed；接線版使用匿名、分 scope 的 same-origin session，
完整 Case ID 是查詢最小狀態的 bearer capability，不要求 user ID 或 OAuth。

## 現行介面契約

- 案號以信用卡式欄位分成 `C##`、六碼識別碼、`MMDD`、`HHMM`，隱密案件另有
  選填末碼 `P`。
- 分段欄位會轉成大寫、移除不允許字元並自動前進；整串案號可直接貼上並拆分。
- 一般與 `-P` 使用同一介面，不要求第二組短驗證碼。
- 頁面標示「測試中」，表示狀態可能延遲或不可靠，不代表案號禁止轉傳。
- 結果只顯示：案號、一般／隱密、五態之一、最後更新、是否已有教學團隊回覆、
  Discord 直達連結。
- 不顯示題目、回覆內容、作者、班級、附件、AI 選擇、Discord／SQLite 內部 ID。
- 單次查詢，不使用 polling 或背景 timer。

## 2026-08-24 桌面驗收

| 情境 | 輸入 | 結果 |
| --- | --- | --- |
| 一般案 | `C01`／`7K4M2Q`／`0702`／`1000` | 通過；顯示一般案件、安全狀態摘要與 fixture Discord 連結。 |
| 隱密案 | `C99`／`B4W9K6`／`0702`／`1500`／`P` | 通過；顯示隱密案件與安全狀態摘要，不揭露內容或內部識別碼。 |
| 大小寫 | 分段輸入 `c99`／`b4w9k6`／`p` | 通過；整理成大寫 canonical 案號。 |
| 無直達連結 | 隱密 fixture | 通過；只提示從 Bot 私訊或伺服器返回，不產生虛假 URL。 |
| Public build | `http://127.0.0.1:4330/cases/` | 通過；所有分段與按鈕停用，顯示「案件查詢服務尚未啟用」。 |

## Privacy 與 artifact 邊界

- `listPublicCases()` 仍排除 Private Support 全文 projection。
- `listCaseStatuses()` 才能提供 `-P` 的 content-free 狀態 projection；測試固定欄位且拒絕
  title、message、attachment、author、analysis 與 Discord mapping。
- Public build 不攜帶 reviewer fixtures，未接線時不顯示成功結果或虛構 Discord 連結。
- Connected public build 不把 Case ID 寫進 URL；查詢使用 POST、`Cache-Control: no-store`
  與短效 `LOOKUP` session。
- 不存在、無權限與 backend 不可用都應採最小揭露文案，避免案件枚舉。

## 驗證結果

- Portal Vitest：60／60。
- Astro check：66 files，0 error、0 warning、0 hint。
- Public artifact：5 required pages，54 個 base-safe local references，驗證通過。
