# 初始環境診斷

- 診斷日期：2026-07-19（Asia/Taipei）
- 專案根目錄：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`
- 執行原則：只檢查工具與檔名；沒有讀取憑證內容、安裝全域工具或連接外部服務。

## 系統與工具

| 工具                           | 狀態         | 診斷結果                                                        |
| ------------------------------ | ------------ | --------------------------------------------------------------- |
| macOS                          | 已安裝       | macOS 26.5（Build 25F71），Darwin 25.5.0，Apple Silicon `arm64` |
| Git                            | 已安裝       | 2.52.0                                                          |
| Python                         | 已安裝       | CPython 3.14.6                                                  |
| pip                            | 已安裝       | 26.1.2，對應 Python 3.14                                        |
| uv                             | 已安裝，可選 | 位於使用者本機路徑；不得作為唯一安裝方式                        |
| Node.js                        | 已安裝       | 24.13.0                                                         |
| npm                            | 已安裝       | 11.6.2                                                          |
| npx                            | 已安裝       | `/usr/local/bin/npx`                                            |
| Corepack                       | 已安裝       | `/usr/local/bin/corepack`                                       |
| Make                           | 已安裝       | `/usr/bin/make`                                                 |
| clasp                          | 缺少         | shell 路徑中找不到；後續應以 project-local npm dependency 提供  |
| GitHub CLI (`gh`)              | 缺少         | 非本地開發必要條件；目前也未授權建立 remote                     |
| ruff                           | 未全域安裝   | 預期由 Python 專案虛擬環境安裝                                  |
| pytest                         | 未全域安裝   | 預期由 Python 專案虛擬環境安裝                                  |
| mypy                           | 未全域安裝   | 預期由 Python 專案虛擬環境安裝                                  |
| VS Code / Cursor / Sublime CLI | 未驗證       | shell 路徑中找不到 CLI；不代表 GUI 應用不存在                   |
| Vim / Nano                     | 已安裝       | `/usr/bin/vim`、`/usr/bin/nano`                                 |

## 路徑相容性

專案路徑同時包含空格與繁體中文字。以下檢查皆成功：

- shell 以完整引用路徑切換工作目錄；
- Python 3.14 以 UTF-8 讀取 `PROJECT_DEFAULTS.md`；
- Node.js 24 以 UTF-8 讀取相同檔案；
- npm 可在此目錄啟動本機 Node 指令。

結論：目前沒有發現路徑造成的本機工具問題；所有 shell 文件與 CI 範例仍應引用完整路徑或使用 repository-relative path。

## 憑證與敏感設定檢查

只搜尋檔名，不讀取內容。專案根目錄及其相鄰解壓範圍內未發現：

- `.env` / `.env.*`；
- `.clasp.json`；
- `credentials*.json`；
- 名稱含 `secret` 或 `token` 的 JSON 檔。

## 建議的安全工具鏈

- JavaScript/TypeScript：npm workspaces，使用已安裝的 Node 24；在 `package.json` 宣告可接受的 Node 範圍，依實際套件相容性再收窄。
- Python：標準 `python3 -m venv .venv` 為必要支援路徑；`uv` 只作為選用的加速方式。Python 3.14 很新，若 Discord 或 lint 套件尚未支援，應在專案文件與 CI 改用 3.12/3.13 驗證，而不是修改系統 Python。
- 單一命令介面：根目錄 npm scripts 搭配少量跨平台 Python 指令；避免依賴全域安裝。
- 品質工具：Python 採 pytest、Ruff、mypy；TypeScript 採 TypeScript compiler、Prettier 與 Astro/TypeScript 檢查。實際版本與驗證結果見 `docs/IMPLEMENTATION_STATUS.md`。
- 外部工具：`clasp` 後續以 workspace dev dependency 安裝；`gh` 目前不是必要條件。
