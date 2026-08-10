# Config Studio 本機審查指南

Config Studio 是 proposed config 的本機視覺化編輯與比較工具。所有修改只留在目前瀏覽器記憶體；沒有 Discord SDK、token loader、外部 API 或套用按鈕。

## 啟動與停止

在 Terminal 輸入：

```bash
cd "/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案"
npm run review
```

開啟 `http://127.0.0.1:4322/`。目前來源是 `config/proposed/`。完成後回到 Terminal 按一次 Ctrl+C。若只啟動設定台，可執行 `npm run review:studio`，之後用 `npm exec --workspace @calculus/config-studio -- astro dev stop` 停止。

## 每區看什麼

1. 總覽：來源、狀態、安全邊界與變更數。
2. 頻道樹：搜尋、調整排序、重新命名或新增一個本機 draft channel。
3. 身份角色：確認 Student、Guest、special guest、Staff、Administrator、course_assistant 與 dump_bot。
4. 權限矩陣：檢查 effective permissions；Bot 不得有 Administrator，dump_bot 只讀明確範圍。
5. Forum：比較三個 Forum、tags、Module 與 canonical title `[M1][觀念] 標題`。
6. 案件流程：確認 Open → Tracked → Idle → Auto Closed 與手動 Closed、48h＋48h。
7. Private Support：確認 temporary text channel、可見角色、公開查詢關閉與 archive／verify／log／delete sequence。
8. 文件匯入：輸入任意 fixture 文字前必須先選分類；匯入只作 untrusted preview。
9. 差異比較：每項變更需標示 ADD／MODIFY／REMOVE／UNCHANGED。
10. 匯出：JSON、JSON-compatible YAML 與 Markdown 只下載 proposed draft，不會套用。

## 建議操作腳本

- 搜尋 `math`，把 Math Questions 暫改為 Math Help；Diff 應顯示 MODIFY。
- 新增一個 draft text channel；Diff 應顯示 ADD。
- 在文件匯入區先不選分類，確認被拒絕；選「人工備註」後再預覽。
- 匯出 Markdown，確認內容標示 fixture/proposed，且沒有 token 或真實 ID。
- 重新整理頁面，瀏覽器記憶體變更應消失。

## GO-APPLY 邊界

任何匯出都只是審查草稿。未來若要套用，仍需真人核准、隔離測試伺服器、兩隻 Bot Applications、權限與 role hierarchy 檢查、token 安全儲存、普通學生帳號可見性測試及 rollback 演練。
