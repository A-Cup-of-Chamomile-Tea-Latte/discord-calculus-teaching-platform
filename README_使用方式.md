# Codex 指令包使用說明

這個壓縮包不是成品程式，而是一組可以交給 Codex 逐批執行的 `.md` 交接文件。

## 建議放置位置

將本資料夾內容放到：

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

本地資料夾使用中文與空格沒有問題；執行 shell 指令時要完整加引號。遠端 GitHub repository 可另外使用英文名稱，例如 `discord-calculus-teaching-platform`。

## 最先交給 Codex

1. `CODEX_TASKS/00_START_HERE.md`
2. `CODEX_TASKS/BATCH_A_FOUNDATION.md`

Batch A 會先做環境診斷、monorepo、工具鏈、專案前言、架構決策、資料契約與假資料。完成後，再依 `CODEX_TASKS/TASK_MATRIX.md` 分流。

## 每一批都會留下

- 實作結果；
- 測試與 build 結果；
- 診斷問題；
- 假設與風險；
- 下一步建議；
- 可直接貼回 ChatGPT 討論的繁體中文摘要。

## 尚未授權 Codex 做的事情

- 建立或推送 GitHub remote；
- 公開部署 GitHub Pages；
- 建立／部署 Apps Script 雲端專案；
- 寄信；
- 連正式 Discord server；
- 使用真實學生資料；
- 讀取或要求真實 secrets。

## GitHub Pages 預設方向

既有的 `A-Cup-of-Chamomile-Tea-Latte.github.io` 保留。新專案使用另一個 repository 的 project site；Astro build 會預留 repository base path。
