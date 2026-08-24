# 學期、班別與助教配置長期規格

## 目的

此規格保存跨學期穩定的課程營運模型。每學期的實際班別資料位於
`config/academic/<民國學年>-<學期>/course-operations.yaml`，並由
`config/schema/course-operations.schema.json` 驗證。

`115-1` 表示民國 115 學年度第 1 學期，不是西元年份，也不是任意版本號。

## 模型

```text
AcademicTerm（民國學年 + 學期）
└── Module（M1–M4）
    └── ClassSection（C01–C16）
        ├── SourceLabel（例如「模01」）
        ├── InstructorRef
        ├── TeachingAssignment（TA ref + 來源類別代碼）
        └── PracticeSection
            ├── TA ref
            ├── 教室
            └── 分組規則
```

來源 PDF 的「模01」至「模16」是班級標籤，不是 16 個模組。系統將其正規化為
`C01` 至 `C16`，並保留 `sourceLabel` 以便回查原表。115-1 的四個模組對照已由課程
owner 確認：

- `M1 理工電資`：`C01–C04`；
- `M2 土木機電`：`C05–C09`；
- `M3 經濟商管`：`C10–C13`；
- `M4 農學院`：`C14–C16`。

此 mapping 在 repository spec 中為 `APPROVED`；這代表課程資料已確認，不代表已套用至 Discord。

選修或未納入一般流程的外部班別從 `C21` 開始排號；`C17–C20` 刻意保留不用。
115-1 來源只能辨識一個「乙(醫)」班別，因此目前保留為 `C21`、
`REFERENCE_ONLY_PENDING_CONFIRMATION`。若後續有可辨識的新班別，依序使用 `C22`、`C23`…；
未啟用者不出現在學生註冊清單。`C99` 仍專用於 Private Support 等特殊案號，不代表班別。

## TA 類別

來源使用 `L`、`G`、`G/L`，tracked spec 正規化為 `L`、`G`、`G_L`；若來源空白則為
`UNSPECIFIED`。課程 owner 已確認對應：

- `L` → `TA Lecturer`；
- `G` → `TA Grader`；
- `G/L` → 同時具有 `TA Lecturer` 與 `TA Grader`。

實習課分組表中的 TA 必須能在同班名冊找到，且來源類別為 `L` 或 `G_L`。

這份配置只描述已提供的 assignment，不評價 TA、不推論工作量，也不把人員配置轉換為績效排序。

## 註冊與 Discord membership

學生在網頁註冊時從當期 active class list 選擇 Class，後端再由已核准的
Class → Module mapping 推導 Module。不讓學生另外選擇 Module，避免兩個欄位互相矛盾。

現行 Discord membership 模型足夠承載此設計：學生取得一個 broad course membership role 與一個
allowlisted Class role；Module 只存在後台資料，不另建 Discord role。註冊頁的 Class 選擇只決定班別，
不自動證明學生具有課程資格；課程 membership 授權仍必須經過獨立的身分／啟用流程。

## 分組規則

預設規則是「學號末三碼除以該班實習課 TA 數的餘數」。每個 practice section 保存來源中的餘數或
`ALL_STUDENTS`，以及實習課教室。若班級自行分配，來源要求於開學後第三週回傳名單；來源未標示
哪些班級採自行分配，因此不得自行指定。

## 個資分層

Tracked spec 保存：

- 班別、Module、教室與分組規則；
- opaque `instructorRef`／`taRef` 與公開顯示姓名；
- 來源類別代碼與 source receipt。

115-1 來源 PDF 是課程公開營運資料，可保存在 `docs/sources/115-1/` 作 canonical source。為避免同一份
聯絡資料被結構化複製後漂移，tracked spec 仍只抽取本系統需要的班別、姓名、角色、教室與分組資訊；
學號、電話、Email、系所／年級以來源 PDF 為準，不另寫入 course spec、Google Sheet 或 Bot DB。

若本機需要 person ref 查找，可在 `.local/course-data/<term>/` 建立 owner-only working directory；
它是可重建的 operational index，不是第二份 canonical source。

## 115-1 canonical entry

- Term spec：`config/academic/115-1/course-operations.yaml`
- Source receipts：`config/academic/115-1/source-receipts.json`
- Local person index：`.local/course-data/115-1/private-directory.json`（可重建、Git-ignored）
- Public source PDFs：`docs/sources/115-1/`

Spec 是本機／repository 的課程配置權威，但不等於 Discord 已套用。任何 Discord role、channel、
permission 或學生 membership 變更仍須走 provisioning preview、diff、明示 apply gate 與 rollback。
