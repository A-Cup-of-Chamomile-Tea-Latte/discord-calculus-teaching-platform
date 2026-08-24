# 115-1 課程營運來源

本目錄保存使用者確認可公開參照的 115 學年度第 1 學期課程營運文件：

- `1151實習課分組方式及地點.pdf`：模班、教師、實習課 TA、教室與分組餘數。
- `1151各班TA資料.pdf`：各模班的 TA 類別與公開聯絡資料。

系統抽取後的班別／模組／TA 配置位於 `config/academic/115-1/course-operations.yaml`，來源 hash 與
頁數位於 `config/academic/115-1/source-receipts.json`。PDF 是聯絡資料的 canonical source；不要再把
學號、電話、Email、系所／年級複製到 Bot DB、Google Sheet 或另一份 tracked directory。

PDF 中「模01–模16」是來源班別標籤，系統正規化為 `C01–C16`。課程 owner 已確認
四個 Module：`M1 理工電資（C01–C04）`、`M2 土木機電（C05–C09）`、
`M3 經濟商管（C10–C13）`、`M4 農學院（C14–C16）`。此對照可供 repository 與本機
Config Studio 審查；尚未套用到 production Discord。

「乙(醫)」在來源中是一個合併班別列，下方三列為三位 TA，不是三班。系統將其保留為
未啟用的 `C21`；若未來來源新增可辨識的外部班別，依序使用 `C22`、`C23`…。
