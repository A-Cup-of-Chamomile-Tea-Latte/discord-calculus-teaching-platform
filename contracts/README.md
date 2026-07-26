# Contracts

跨 Portal、GAS、bots 與 tools 共用的版本化 JSON Schema、相容性規則與範例。不得放服務憑證、框架專屬內部物件或真實資料。

Working／Archive fixture model 使用 `active-case`、reduced `case-projection`、`user`、
`consent`、`sync-state`、`changed-case-queue`、`archive-index`、`export-manifest`、
`sanitized-package`、`weekly-maintenance-run`。`discord-structure-inventory` 僅允許結構欄位，
禁止訊息內容與 member list。邊界與 rollover 見
[`docs/architecture/WORKING-ARCHIVE-DATA-MODEL.md`](../docs/architecture/WORKING-ARCHIVE-DATA-MODEL.md)。
