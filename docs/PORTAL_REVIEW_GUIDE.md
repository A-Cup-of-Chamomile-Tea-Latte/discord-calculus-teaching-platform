# Portal 本機審查指南

本指南只審查虛構資料與本機介面。它不會連接 Discord、Google、Email、OAuth 或 AI API，也不會部署。

## 啟動與停止

在 Terminal 輸入：

```bash
cd "/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案"
npm run review
```

開啟 `http://127.0.0.1:4321/`。完成後回到 Terminal 按一次 Ctrl+C；Portal 與 Config Studio 都會停止。若只想看 Portal，可執行 `npm run review:portal`，之後用 `npm exec --workspace @calculus/portal -- astro dev stop` 停止。

## 建議審查順序

1. 首頁：確認七個主要入口、NTU COOL 分工與案號查詢。
2. 加入／設定：確認 Discord、Email、班級／Module、顯示名稱、隱私、規則及完成步驟都明示為 fixture。
3. Discord 直接提問：確認流程是「學生本人發文 → 選單補充屬性 → Bot 整理標題與標籤 → 建立案件」。
4. 網站代為提問：不選 AI Yes／No 先送出，應看到可讀錯誤；補齊後只產生未持久化 confirmation。
5. 案號查詢：正常案號用 `C01-7K4M2Q-0702-1000`；不存在用 `C01-Z9Y8X7-0702-2359`；錯誤格式用 `hello`。
6. 案件頁：檢查遮罩案號、Last Update／Response／Synced、附件 marker、文字對話、Discord fixture 連結與結案／重新開啟預覽。
7. Private Support：確認可見對象、附件、明確 AI Yes／No、不可公開查詢與 fixture confirmation。
8. 我的設定、指南、系統狀態、教學團隊與情境庫：確認都沒有真實帳號或管理寫入功能。

## 兩種外觀

頁首的「切換學生友善版／切換課程正式版」按鈕可在相同元件上切換設計變數。選擇只存於瀏覽器 `localStorage`，不會送出。正式預設建議採「課程正式版」；「學生友善版」保留作低門檻入口比較。

## 可操作與展示邊界

- 可操作：導覽、外觀切換、案號查詢、fixture 表單驗證與 confirmation、案件狀態預覽。
- 只展示：Discord 連結、Email、同步、教學團隊佇列、結案與 Private Support 建立。
- 不存在：登入、真實送出、持久化、外部 API、檔案上傳、部署。

## 鍵盤與窄螢幕

用 Tab／Shift+Tab 走過 skip link、導覽、外觀切換、表單與按鈕；焦點應清楚。用瀏覽器窄化到約 375 px，頁面不得水平爆版。錯誤與狀態均有文字，不只靠顏色。
