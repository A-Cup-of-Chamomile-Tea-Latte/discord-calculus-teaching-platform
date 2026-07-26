# Fixtures

供 Portal、GAS、bots 與 tools 共用的穩定、可讀、完全虛構資料。所有 email 使用 `example.com`，所有姓名、Discord ID、內容、hash 與時間都為人工設計的測試值。

## Seed

1. 以 `MANIFEST.json` 的 `recordSets` 順序載入 JSON arrays。
2. 每個 item 以列出的 Task 07 schema 驗證後才交給 consumer。
3. 以 `adapters/mock-adapters.json` 選擇 service scenario；不得在 fixture mode fallback 到真實網路。
4. 跨元件 happy path 固定使用 `case_000421` / `C01-7K4M2Q-0702-1000`。

## Reset

Fixtures 是 immutable source of truth，測試不得原地寫回。每次測試以重新讀取 JSON 建立 in-memory copy；若測試需要 mutation，使用暫存目錄或 deep copy，結束後丟棄。若 fixture 內容被手動修改，執行：

```sh
source .venv/bin/activate
python -m pytest tests/contract/test_fixture_scenarios.py
npm run check
```

不要把真實 export 複製到 `fixtures/exports/`；真實／本機資料只能放在被 Git ignore 的根層 `exports/` 或 `local-data/`。

`discord/structure-inventory.json` 是 structure-only server fixture；`provisioning/` 是宣告式
current/desired server plan。兩者都不得替換成真實 server dump。Synthetic actors 定義與真人測試
限制見 `docs/testing/SYNTHETIC-DISCORD-ACTORS.md`。
