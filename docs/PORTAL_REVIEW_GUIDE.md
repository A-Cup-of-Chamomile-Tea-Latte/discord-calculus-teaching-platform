# Portal 本機審查指南

更新日期：2026-08-24

## 啟動

```bash
cd "/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案"
npm run review
```

開啟 `http://127.0.0.1:4321/`。這是 reviewer build，不會部署，也不代表 Portal backend 已接線。

## 2026-08-24 驗收結果

- Reviewer artifact：16 頁完整；public artifact：5 頁，10 個內部／封存 route tree 與 3 個 internal-only assets 已排除。
- Public 四個學生頁在 390px 手機寬度無橫向溢出、無內部連結、無 browser console warning／error。
- Public 案件查詢在 backend 未接線時停用，不顯示 fixture 成功結果或虛構 Discord 連結。
- A4 landscape 列印共 10 頁，已逐頁檢查中文字型、標題、表單、警示色、分頁與裁切。

## 本輪審查順序

1. 首頁：Hero、紅色 NTU COOL 警示、三個主要入口與平台分工。
2. 加入：學生／訪客欄位、Discord username、正式班別標籤、單一送出動作。
3. 查案件：信用卡式分段輸入同時接受一般／`-P`，只顯示狀態摘要，不出現內容或詳情頁。
4. 使用指南：公開／隱密 Discord 流程、三個提問區、逐案 AI 同意、DM 與 FAQ。
5. 內部登入：從 `http://127.0.0.1:4321/access/?role=admin` 進入；助教／教師與
   系統管理員是兩級權限，第一位本機管理員就是 reviewer 的最高本機權限。
6. 加入申請：兩級審核權限、等待 Discord 成員與可逆封存 stage。
7. 管理員狀態：建造 gate 與未來 monitor dashboard 的切換條件。
8. 舊路由：`/ask/`、`/private-support/`、`/discord-guide/` 只應顯示封存提示；公開 artifact 不得包含。

## 視覺基準

採深綠、暖白與燙金重點色。頁首維持精實，不放「課程入口預覽」肥標籤。學生文字以自然繁中為主；英文只保留產品名稱、指令與必要術語。字級應有清楚層級，但卡片不靠超大字製造重要性。

## 安全邊界

- reviewer build 可操作本機欄位驗證與 browser-only 身份展示。
- 尚未接線：正式加入申請、單案 lookup backend、Discord role write。
- Public build 不得包含 fixture 案件內容、內部登入、狀態 dashboard、舊路由或管理工具。
- Runtime 以最新 canonical repo 與 AI 交接核對；Portal 工作不得機械覆寫 production v6 支線。
