# 微積分教學支援平台

這個專案協助同學在 Discord 提問，也讓助教比較容易整理、回覆和追蹤問題。學生入口網站則負責使用說明、隱私提醒與流程預覽。

教材、作業、成績、截止日期、正式公告和課程政策仍以 **NTU COOL** 為準。本平台處理的是提問與教學支援，不會取代正式課務系統。

> **目前狀態**
>
> Discord 與遠端 Bot 已有實際運作環境，但仍有結案後立即重新提問的一致性問題待修正。公開 Portal 目前是展示版，表單和案件查詢使用虛構資料，不會真的送出學生內容。正式學生試用、Email、Private Support backend 與教學分析尚未因網站公開而自動啟用。最新進度請看[實作狀態](docs/IMPLEMENTATION_STATUS.md)和[下一步](docs/NEXT_STEPS.md)。

## 同學會怎麼使用

1. 教材、作業與正式公告回 NTU COOL 查看。
2. 一般問題到 Discord 對應的 Forum 發文。
3. Bot 引導同學補上關鍵字，並選擇是否同意後續教學分析。
4. 系統整理文章標題、建立案件編號，助教直接在原討論串回覆。
5. 結案後如果還有疑問，原發文者可以重新開啟同一個案件。

敏感問題不要貼到公開討論區。請使用課程另外公告的受保護管道；目前公開 Portal 的 Private Support 頁面只是流程示範。

## 三個入口各自負責什麼

| 入口     | 用途                                       |
| -------- | ------------------------------------------ |
| NTU COOL | 教材、作業、成績、期限、正式公告與課程政策 |
| Discord  | 提問、回覆、討論與助教支援                 |
| Portal   | 使用說明、隱私提醒、流程預覽與虛構案件展示 |

## 在自己的電腦預覽網站

需要 Node.js 24.x 與 npm 11.x。第一次執行：

```sh
npm install
npm run dev --workspace @calculus/portal
```

開啟終端顯示的本機網址。可用展示案號 `C01-7K4M2Q-0702-1000` 試用案件查詢。加入、一般提問與 Private Support 表單只會在目前頁面顯示確認結果，不會儲存或傳送內容。

## 沒有 AI 也能維護

網站沒有把 AI 當成建置或發布的必要條件。一般維護只需要文字編輯器、Node.js、Git 和 GitHub 帳號。

常用位置：

- 修改頁面文字：`apps/portal/src/pages/`
- 修改共用頁首、頁尾或元件：`apps/portal/src/components/`
- 修改網站外觀：`apps/portal/src/styles/`
- 修改學期、班別與課程設定：`config/academic/`
- 查看目前有效狀態：`docs/IMPLEMENTATION_STATUS.md`、`docs/NEXT_STEPS.md`

每次修改 Portal 後，依序執行：

```sh
npm run check --workspace @calculus/portal
npm run test --workspace @calculus/portal
npm run dev --workspace @calculus/portal
```

前兩個指令檢查程式與測試；第三個指令讓維護者親自用瀏覽器確認畫面。發布前至少檢查首頁、導覽、手機寬度、一般提問、案件查詢與 Private Support 說明。

如果變更造成問題，不要刪除歷史或強制覆蓋遠端。使用 GitHub 的 **Revert**，或在本機執行下列指令建立一筆反向提交：

```sh
git revert <造成問題的 commit>
git push
```

這樣可以回復網站，同時保留誰在什麼時候改了什麼。

## 發布 GitHub Pages 展示版

本專案已準備 GitHub Actions。正式發布前先在本機建立公開版並檢查輸出：

```sh
ASTRO_BASE_PATH=/discord-calculus-teaching-platform \
ASTRO_SITE_URL=https://A-Cup-of-Chamomile-Tea-Latte.github.io \
npm run build:public --workspace @calculus/portal

npm run verify:public --workspace @calculus/portal -- \
  /discord-calculus-teaching-platform/
```

檢查通過後：

1. 將經過審查的 commit 推到 GitHub 的 `main` branch。
2. 到 repository 的 `Settings → Pages`，將 Source 設為 `GitHub Actions`。
3. 到 `Actions → Pages project-site → Run workflow`，把 `deploy` 設為 `true`。
4. 開啟部署網址，重新檢查首頁、導覽、表單說明與手機版面。

完整發布與回復說明見 [GitHub Pages 指南](apps/portal/docs/GITHUB_PAGES.md)。

## 公開前要守住的界線

- GitHub Pages 是全網公開網站，不是課程登入系統。
- 不得提交真實姓名、學號、Email、Discord ID、Private Support、訊息匯出或附件。
- 不得提交 `.env`、Bot token、OAuth credential、deployment ID 或 SQLite 資料庫。
- `fixtures/` 只能放虛構資料；公開頁面也只能讀取公開版允許的內容。
- 表單送出、正式案件查詢與 Private Support 必須另有身分驗證、權限控制和後端服務，不能只靠 GitHub Pages。

## 專案地圖

| 位置                           | 內容                             |
| ------------------------------ | -------------------------------- |
| `apps/portal/`                 | 學生入口網站                     |
| `runtime/discord-course-bots/` | 目前追蹤的 Discord Bot runtime   |
| `config/`                      | 課程、班別、案件流程與伺服器設定 |
| `fixtures/`                    | 測試與展示用的虛構資料           |
| `contracts/`                   | 元件交換資料時共同遵守的格式     |
| `tests/`                       | 自動檢查與回歸測試               |
| `docs/`                        | 操作指南、現況、決策與歷史證據   |

## 依身分閱讀

- 教授或審閱者：[提案前言](docs/PROPOSAL_PREFACE_DRAFT.md) → [實作狀態](docs/IMPLEMENTATION_STATUS.md)
- 學生：[學生快速指南](docs/guides/STUDENT_QUICK_GUIDE.md)
- 助教：[助教快速指南](docs/guides/TA_QUICK_GUIDE.md)
- 網站維護者：[Portal 開發指南](apps/portal/docs/DEVELOPMENT.md) → [GitHub Pages 指南](apps/portal/docs/GITHUB_PAGES.md)
- 系統維護者：[文件總覽](docs/README.md) → [設定總覽](docs/CONFIGURATION.md) → [操作員流程](docs/OPERATOR_WORKFLOW.md)

完整專案檢查需要 Python 3.12–3.14。環境安裝、完整測試與 fixture 資料流示範請看[本機開發指南](docs/architecture/DEVELOPMENT.md)和 [Fixture demo](docs/FIXTURE_DEMO.md)。
