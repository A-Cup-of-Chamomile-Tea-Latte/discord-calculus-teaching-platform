# Discord bots

多 bot 架構與共用 Python 核心。每個實際 bot 使用獨立 application/token、separate runtime config 與最小權限；本目錄不存 token、不連正式 server，也不承擔入口網站 UI。

責任、permissions/intents、commands、event ownership、failure isolation與single-bot reversal見 [`ARCHITECTURE.md`](ARCHITECTURE.md)。Service/adapter ports見 [`docs/architecture/BOT_SERVICE_INTERFACES.md`](../docs/architecture/BOT_SERVICE_INTERFACES.md)。

結構盤點與明確匯出的 canonical package 是 [`dump_bot`](dump_bot/README.md)；
`archive_reader` 暫留為相容名稱，不啟動 polling 或真實 Discord 連線。
