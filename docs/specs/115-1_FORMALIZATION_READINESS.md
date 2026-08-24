# 115-1 班別設定正式化準備度

## 目前狀態

115-1 課程資料已成為 repository 內可驗證的 canonical term spec，但尚未套用到
Discord production。「資料正式化」與「對外套用」是兩個獨立 gate。

## 已完成

- 兩份公開課程營運 PDF 已移入 `docs/sources/115-1/`，並有 source receipt、頁數與 hash。
- `115-1` 固定解釋為民國 115 學年度第 1 學期。
- 來源的「模01–模16」已正規化為 `C01–C16`，並保留 `sourceLabel` 回查原表。
- 四個模組對照已確認：`M1 C01–C04`、`M2 C05–C09`、`M3 C10–C13`、
  `M4 C14–C16`。
- 教師、TA 公開顯示姓名、TA 來源類別、教室與分組規則已結構化。
- TA 類別已確認：`L → TA Lecturer`、`G → TA Grader`、`G/L → 兩者`。
- 「乙(醫)」來源只能辨識一班，已保留為未啟用的 `C21`；未來新增外部班依序使用
  `C22`、`C23`…。
- 學生在網頁註冊時選擇 active Class，Module 由後端 mapping 推導。
- Discord 沿用 broad course role＋allowlisted Class role；Module 不另建 role。
- Schema 與語意驗證已覆蓋班別完整性、Module mapping、person ref、practice TA 及公開來源收據。
- Config Studio 已有只讀的「115-1 班別」審查頁。

## 對外套用前必須決定

1. `[NEEDS PROFESSOR INPUT: 確認網頁註冊前的課程 membership 啟用方式；Class 可由學生自選，但 NTU email 或 Class 選擇本身不證明具有課程資格。]`
2. 為班別設定建立獨立的 preview、diff、apply 與 rollback gate；不得把既有
   `GO-LIVE-CUTOVER` 當成新的 Discord 資源或 membership 修改授權。

## 仍可在未套用 production 前進行

- 從 term spec 產生不含密密資料的 provisioning preview。
- 唯讀盤點現有 Discord 與 proposed config，產生 add／modify／remove／unchanged diff。
- 對 fixture guild 驗證 class mapping、重複套用的 idempotency 與 rollback。
- 確認聯絡資料不會被複製到 Discord、Google Sheet 或 Bot DB。
- 將已批准的決定寫回 canonical spec，再更新主線的 ordered next steps。

## 停止條件

未完成上述決定、沒有可審查 diff、沒有 rollback，或沒有使用者針對本次套用的明示授權時，
不得修改 production Discord。
