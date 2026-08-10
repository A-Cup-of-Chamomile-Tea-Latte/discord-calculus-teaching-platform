# Discord 微積分模組教學優化專案：NAP BUILD 完成報告

日期：2026-07-28
時區：Asia/Taipei
Canonical root：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`
分支：`codex/nap-build-20260728`

## 完成狀態

**本機 GO-BUILD 完成。真實服務、部署與 GO-APPLY 維持 NO-GO。**

工作包已移至 `project-exchange/Codex_午睡大工程_GO-BUILD_本機工作包.md`。SHA-256：

`6a5f3fcecea46ac6e5ae0a05e7ca87b32efd467082a5e14db81f9034719e8678`

本輪沒有 Discord 寫入、Discord token 讀取、Google／Email／OAuth／AI API 連線、部署、push 或真實學生資料處理。

## 來源與決策處理

- `project-exchange/10_CFG_DiscordSide.zip` 是最高優先、已確認的最新 Discord Side 設定來源。
- `project-exchange/14_Discord_112_113_114_三年比較分析包.zip` 只讀取獲准的彙總結論與結構統計；沒有讀 raw messages、姓名、ID、Email、附件內容、Private Support 或帳號集中度細節。
- 最新 lifecycle 是 Open／Tracked／Idle／Closed／Auto Closed，48h＋48h；Task 34 的舊 domain values 保留相容並明確列為 drift。
- Canonical `IMPLEMENTATION_STATUS.md` 已更新至 2026-07-28；非 canonical thread cwd 不再當成受管位置，解決文件與受管資料分裂。

## 主要成果

1. `config/proposed/`：server、portal、case workflow、data policy 四份 JSON-compatible YAML。
2. `config/schema/`：四份 Draft 2020-12 schema；validator 額外檢查引用、重複、矛盾權限、Forum tags、Private Support、AI choice、Bot allowlist 與 `dump_bot` public read-only boundary。
3. `docs/generated/`：11 份 deterministic 文件，包括 channel tree、permission matrix、Forum tags、bot permissions、lifecycle、page map、summary、drift、decision migration、evidence matrix。
4. `apps/config-studio/`：十區本機設定台，可編輯 channel tree、檢查 roles/effective permissions/Forum/workflow/Private Support、分類 untrusted import、看 diff、匯出 proposal。
5. `apps/portal/`：兩種 design-token theme、完整學生入口與團隊／情境審查頁，明確 fixture、AI Yes／No、附件 marker、Private Support 邊界與最新 lifecycle。
6. `tools/discord_provisioning/`：fixture plan、diff、rollback、readiness 與 memory-only fake apply；支援 idempotency、partial failure resume、不刪 unmanaged resources。
7. `npm run review`：同時啟動 Portal 4321 與 Config Studio 4322，顯示 fixture 案號與 config 路徑，Ctrl+C 可靠停止兩站。
8. Markdown review guides、同源 RTF、architecture、open issues、GO-APPLY gates、時間紀錄與 screenshots。

## 驗證結果

| Gate                | 結果                                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| Root check          | PASS                                                                       |
| Secret scan         | 528 candidate files，0 findings                                            |
| Python tests        | 169/169 PASS                                                               |
| Portal tests        | 43/43 PASS                                                                 |
| Config Studio tests | 3/3 PASS                                                                   |
| GAS tests           | 48/48 PASS                                                                 |
| Astro diagnostics   | Portal 53 files、Studio 7 files；0 error/warning/hint                      |
| Python lint/type    | Ruff PASS；mypy 98 source files PASS                                       |
| Build               | Portal 18 pages；Config Studio 1 page；GAS bundle PASS                     |
| Pages base path     | 273 local references verified under `/discord-calculus-teaching-platform/` |
| Static footprint    | Portal 約 312 KB、4 JavaScript files                                       |
| Browser console     | 0 error/warn                                                               |
| Screenshots         | 9 張；1440×900、1280×800、1024×768、375×800                                |
| Fresh extraction    | isolated npm/Python install、full check、base-path build/verify PASS       |

Python 唯一警告是 discord.py 在 Python 3.14 的兩個既有 `asyncio.iscoroutinefunction` deprecation warnings。

## 瀏覽器操作結果

- 首頁主要入口與兩種 theme：PASS。
- 正常案號、前後空白 normalization：PASS。
- 不存在案號不揭露 Private Support：PASS。
- 錯誤格式：PASS。
- 一般問題未選 AI Yes／No：正確阻擋並顯示可讀錯誤。
- 一般問題完整 fixture confirmation：PASS；不送出、不持久化。
- Private Support No choice 與 confirmation：PASS；public lookup 關閉。
- Tracked、Idle、手動 Closed、Auto Closed、新 Cycle preview：PASS。
- 附件 marker、離線／同步落後／未完成文章屬性等 16 個情境：PASS。
- Config Studio channel rename/add、ADD/MODIFY diff、effective permission、import classification：PASS。
- 375 px Portal／Studio document-level `scrollWidth == clientWidth`。
- Accessibility 結構：skip link、landmarks、labels、radios、checkboxes、文字狀態與 focus-visible CSS 均存在；仍需真人在一般桌面瀏覽器做最後 zoom／contrast／focus-order spot check。

瀏覽器 full-page stitching 的重複中間圖未納入交接；只保留命名與像素尺寸一致的 9 張審查圖。

## 安全與資料邊界

- Portal/Studio source 沒有 `fetch`、XHR、WebSocket、sendBeacon 或 Google API。
- Static output 唯一外部 domain 是 fixture Discord deep link；沒有外部字型、圖片、analytics 或 CDN。
- `Administrator` 永遠不在 Bot permission allowlist。
- `dump_bot` 對公開 Questions／Resources 明確只有 VIEW/EXPORT，拒絕 POST/REPLY/MANAGE；Private Support cleanup 與 system-log 另用白名單 override。
- Private Support 對 Student／Guest 明確 deny VIEW。
- Packaging 排除 `.git`、`.env*`、credential/token patterns、`.venv`、`node_modules`、cache、build outputs、舊 ZIP、operator data 與 symlinks；保留 fixtures、generated docs、screenshots、tests、proposed config 與 RTF。

0 secret finding 是文字掃描結果，不等於 malware、binary secret 或 institution privacy certification。

`npm audit` 回報一個 high advisory：`fast-uri` 3.1.3，路徑為 `@astrojs/check` → language server → YAML tooling → `ajv`。它是 transitive dev-only dependency，沒有進入 Portal 的四個 static JavaScript files。為避免破壞 lockfile，本輪沒有執行 `npm audit fix`；應等上游相容更新後升級並重跑全部 gate。

## 已解決問題

1. root script 找不到 `python`：以專案 `.venv/bin` 前置完成基線與 final gate。
2. 一次誤把 `.yaml` 交給 Ruff 造成 trailing commas：立即用 JSON parser 正規化並重跑生成／測試，無外部影響。
3. Astro background server 使第一版 launcher 不能清理：改成明確 background start/stop，Ctrl+C 實測通過。
4. Config Studio Bot 權限把公開區誤顯示為不可見：補上明確 channel overrides、public read-only validator、重產文件並複驗。
5. Pages verifier 第一次使用錯誤介面：base build 成功；以 verifier 所需命令列參數重跑後通過。

## 重要未決

本機沒有 blocking issue。正式下一步有 4 類 P0：

1. legacy lifecycle domain migration 與資料相容策略；
2. retention/deletion/backup/consent 與 named owners；
3. authenticated Portal one-case production boundary；
4. 兩隻 Bot apps、role hierarchy、Private Support visibility 與 rollback 的隔離伺服器實測。

其餘項目見 `docs/reports/NAP_BUILD_OPEN_ISSUES.md`。所有 GO-APPLY 前置條件見 `docs/reports/NAP_BUILD_GO_APPLY_GATES.md`。

## 時間

開始：12:05:06
主要實作完成：12:36 左右
完整 check：12:49:30
build/base-path gate：12:50:06
fresh extraction gate：12:55:16
完成：12:57:39
後續文件與封裝時間見 `docs/reports/NAP_BUILD_TIMELINE.md`。

## 交接檔案

- Portal guide：`docs/PORTAL_REVIEW_GUIDE.md`／`.rtf`
- Config Studio guide：`docs/CONFIG_STUDIO_REVIEW_GUIDE.md`／`.rtf`
- Screenshots：`docs/screenshots/`
- Open issues：`docs/reports/NAP_BUILD_OPEN_ISSUES.md`
- GO-APPLY gates：`docs/reports/NAP_BUILD_GO_APPLY_GATES.md`
- Final ZIP：`project-exchange/Discord_微積分模組教學優化專案_NAP_BUILD_2026-07-28.zip`

## Packaging receipt

為避免 archive 把自己的 SHA 寫入自己造成循環，交接 ZIP 內的本報告停在 freeze 說明；本 canonical working copy 記錄最終 receipt：

- 項目數：535 files
- 大小：1,135,319 bytes
- SHA-256：`9d1e7838bf9fdf847939006125aaffaf649b7882dba78b7edf4fb2b833f49954`
- `unzip -t`：PASS
- 排除清單檢查：PASS；只保留允許的 `.env.example` 與 `fixtures/exports/`
- Fresh extraction：新 npm install、新 Python venv、full check、18-page Pages base build 與 273-reference verifier 全部 PASS

Fresh extraction 的 offline-only 預試因 cache 缺包而失敗；一般 npm 預試又遇到使用者全域 cache 權限錯誤。本輪沒有刪除或 force 該 cache，改用 extraction 目錄內的隔離 npm/pip cache 後通過。驗證暫存目錄完成後已回收。

## 停止點

依使用者指示，本輪完成後停止。下一步等待 online GPT 討論後的新指令；不得自行進入下一輪開發、部署或 GO-APPLY。
