# Fixture demo 指南與口頭腳本

## Demo 保證

本流程只讀取 repository fixtures、啟動 localhost Portal，並寫入 Git-ignored 本機目錄。它不需要 secrets，不連 Discord / Google / email / OAuth，不建立 remote resource，不 deploy。

## 0. 準備

從 repository root 執行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm install
npm run check
```

若 `.venv` 與 dependencies 已安裝，只需 `source .venv/bin/activate` 與 `npm run check`。

## 1. Portal（約 4 分鐘）

```sh
npm run dev --workspace @calculus/portal
```

開啟終端顯示的 localhost URL。示範人可照讀：

> 這個 Portal 是 Astro static prototype，現在讀的全是虛構 fixtures。教材、作業、成績、期限與正式公告仍以 NTU COOL 為準。

操作：

1. 在首頁案件查詢輸入 `C01-7K4M2Q-0702-1000`，顯示一般案件狀態與虛構回覆。
2. 輸入 `C01-Z9Y8X7-0702-2359`，顯示 not-found 與可行下一步；說明 Private Support 也不會透過此查詢暴露存在與否。
3. 進入「透過網站代送」，完成一個表單到 confirmation；指出「Fixture mode · 不會送出」。
4. 進入 Private Support，說明這是獨立、教學團隊限定、預設排除分析的路徑；目前表單同樣只是本頁 fixture confirmation。
5. 進入「使用與隱私指南」，指出作者顯示、可見範圍、analysis permission 是三個不同決定。
6. 進入「系統狀態」，確認 Discord / GAS / Sheets / email 標示為未連接，並提供 fallback。

結束 Portal dev server 時按 `Ctrl-C`。

## 2. 管理者明確匯出（約 2 分鐘）

以一個新的 local demo root 避免與先前輸出混用：

```sh
DEMO_ROOT="local-data/task31-demo"
python -m tools.discord_export C01-7K4M2Q-0702-1000 \
  --adapter fixture \
  --output-dir "$DEMO_ROOT/raw" \
  --page-size 2
```

預期產生：

```text
local-data/task31-demo/raw/C01-7K4M2Q-0702-1000/
├── thread.json
├── thread.md
├── metadata.json
└── attachments.json
```

口頭說明：

> 匯出只取得一個明確選定的 general-case thread，不掃描整個 server。raw output 仍有 internal/Discord IDs 與 consent-excluded content，不可直接公開、匯入或送給 AI。

以同一指令再執行一次，CLI 應回報 `unchanged: true`，示範 idempotent rerun。

## 3. 同意過濾與去識別化（約 2 分鐘）

```sh
python -m tools.anonymizer \
  "$DEMO_ROOT/raw/C01-7K4M2Q-0702-1000" \
  --output-dir "$DEMO_ROOT/sanitized"
```

預期產生 sanitized JSON/Markdown、redaction log、consent summary 與 `review-checklist.md`。口頭說明：

> 只有 raw policy 與目前 consent 都是 INCLUDED 的訊息才保留內容；其餘用無原文的 placeholder 保留時間與回覆關係。自動去識別化不能保證清除所有間接識別線索，因此 checklist 的人工複核是必要關卡。

## 4. Sheets 匯入 dry-run（約 2 分鐘）

```sh
python -m tools.sheets_importer \
  "$DEMO_ROOT/raw/C01-7K4M2Q-0702-1000/metadata.json" \
  "$DEMO_ROOT/sanitized/C01-7K4M2Q-0702-1000/sanitized-thread.json" \
  --adapter dry-run \
  --batch-size 2
```

Dry-run 只在 stdout 列出 destination sheet、idempotency key 與實際會寫入的 sanitized values；不發 HTTP request，不寫入 Google Sheets，不使用 clasp 傳資料。

## 5. Demo 結論

> 現在驗證的是資訊架構、契約、隱私邊界與可重現的 local workflow，不是已完成的機構整合。正式上線前仍須決定身分驗證、權限、保留、撤回、Pages 公開範圍、Discord / GAS technical spikes 與事故應變。

Demo 產物位於 Git-ignored `local-data/task31-demo/`，可保留作本機比對；不要放進展示用 Git artifact 或任何公開位置。
