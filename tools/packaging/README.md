# Reproducible handoff packaging

此工具用固定檔案順序、固定 ZIP timestamp、固定 `0644` 權限與固定壓縮等級建立
可重現 handoff archive，並以原子 replace 避免留下半成品。

```bash
python -m tools.packaging \
  --root . \
  --output project-exchange/Discord_Project_handoff_YYYY-MM-DD.zip
```

工具會輸出 file count、bytes 與 SHA-256。再次用相同 working tree 與 Python/zlib
環境建立，bytes 與 SHA-256 應相同。

## Inclusion and exclusion policy

- 必須包含 `fixtures/exports/export-manifests.json`；缺少時打包直接失敗。
- `fixtures/` 是可提交的虛構測試資料，不因子目錄名為 `exports` 而排除。
- 只排除 root `exports/`、`data/`、`local-data/` 等 operator data。
- 排除 `.git`、環境、dependencies、cache、build outputs、secrets、舊 ZIP 與 symlinks。
- 本工具不讀取真實資料、不連網、不執行部署。

## Fresh-extraction gate

最終交接時由主線建立 ZIP，然後在新的暫存目錄執行：

```bash
unzip -t project-exchange/Discord_Project_handoff_YYYY-MM-DD.zip
mkdir /tmp/discord-handoff-check
unzip project-exchange/Discord_Project_handoff_YYYY-MM-DD.zip -d /tmp/discord-handoff-check
cd /tmp/discord-handoff-check
npm ci
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
PATH="$PWD/.venv/bin:$PATH" npm run check
ASTRO_BASE_PATH=/discord-calculus-teaching-platform \
  ASTRO_SITE_URL=https://example.github.io npm run build
```

執行前使用新的空白暫存目錄；驗證完成後記錄 archive SHA-256、測試數與 build
結果。這是本機 fixture gate，不代表允許 push、部署或連線 Discord／Google。
