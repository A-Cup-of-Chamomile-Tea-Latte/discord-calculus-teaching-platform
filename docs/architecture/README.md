# Architecture

保存系統邊界、資料流與責任表。架構文件不得把 proposed prototype 描述成已核准的正式部署。

- [`CONTEXT.md`](CONTEXT.md)：系統脈絡、信任邊界與mock data flow。
- [`OVERVIEW.md`](OVERVIEW.md)：給審查者的架構摘要、資料路徑與 Astro/template 定位。
- [`COMPONENTS.md`](COMPONENTS.md)：元件責任與明確非責任。
- [`DEVELOPMENT.md`](DEVELOPMENT.md)：安裝、本機命令、base-path dry run 與預覽檢查。
- [`BOT_SERVICE_INTERFACES.md`](BOT_SERVICE_INTERFACES.md)：course writer/archive reader application services與narrow ports。
- [`bots/ARCHITECTURE.md`](../../bots/ARCHITECTURE.md)：多bot責任、permissions/intents、commands、event ownership、credential separation與failure isolation。
