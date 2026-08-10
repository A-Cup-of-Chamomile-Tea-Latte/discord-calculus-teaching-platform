# NAP BUILD 執行時間紀錄

時區：Asia/Taipei（UTC+08:00）。時間以 shell timestamp 與階段完成點記錄；短小節點為分鐘級近似值。

| 節點 | 開始 | 完成 | 經過 | 結果 |
| --- | --- | --- | --- | --- |
| 工作包移動與安全邊界 | 12:05:06 | 12:06:17 | 1m11s | 移至 `project-exchange/`；確認 canonical root |
| Git／檔案／秘密盤點 | 12:05:20 | 12:06:23 | 1m03s | 1 commit、dirty tree、無 remote／nested Git；建立 local branch，不做 baseline commit |
| 基線 check／build | 12:06:23 | 12:06:51 | 28s | check、155 Python、43 Portal、48 GAS、build 全通過；0 secret finding |
| 最新設定與三年彙總來源盤點 | 12:07 | 12:11 | 約 4m | 確認 `10_CFG` 為最高優先；只讀比較包安全彙總 |
| Proposed config／schema／generator | 12:11 | 12:18 | 約 7m | 4 config、4 schema、11 generated docs、validator |
| Config Studio | 12:18 | 12:22 | 約 4m | 10 個審查區、3 tests、typecheck/build 通過 |
| Portal 大型改版 | 12:22 | 12:29:05 | 約 7m | 兩種 theme、必要頁面、情境庫、43 tests、18 pages build |
| Provisioning fake tooling | 12:29 | 12:33:18 | 約 4m | plan/diff/rollback/fake apply；9 tests 通過 |
| 一鍵本機審查 | 12:33 | 12:35 | 約 2m | 兩站啟停與 Ctrl+C cleanup 實測 |
| 文件、瀏覽器驗收與交接 | 12:36 | 12:57:39 | 21m39s | Markdown／RTF、9 screenshots、ZIP、fresh extraction gate |

總經過時間：12:05:06–12:57:39，約 52m33s。

## 已排除的小故障

- root script 預設 `python` 不在 PATH：基線以 `.venv/bin` 前置後通過；最終 gate 同樣使用專案 venv。
- Ruff 被誤用於 `.yaml`，加上 JSON trailing commas：立即用 Prettier JSON parser 正規化並重跑生成／測試，沒有外部影響。
- Astro 7 background server 使原 launcher 無法可靠收尾：改用明確 `--background` 與 workspace `astro dev stop`，再次實測成功。
- Fresh extraction 的 offline-only install 因本機 cache 缺包而失敗；正常 npm 又遇到使用者全域 cache 權限問題。沒有刪除或強制修改該 cache，改用 `/tmp` 內隔離 cache 後完整安裝與 gate 通過。

## 後續 GPT Web 最小驗證包

| 節點 | 開始 | 完成 | 經過 | 結果 |
| --- | --- | --- | --- | --- |
| 檔案收斂、隱私再分級、封裝與 fresh extraction 驗證 | 18:32:47 | 18:37:56 | 5m09s | 154 KiB／118 files；單一 Markdown 主報告；排除 RTF、截圖、依賴、舊 ZIP 與身份／訊息／case fixtures；manifest、ZIP integrity、秘密掃描與 extracted 16 tests 全通過 |
