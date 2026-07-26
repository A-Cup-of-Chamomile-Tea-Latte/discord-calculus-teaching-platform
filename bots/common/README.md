# Bot common

共用設定、資料契約、記錄與 Discord helper。不得包含特定 bot 的事件所有權、token 或產品流程。

Task 21 modules：

- `config.py`：course assistant/archive reader named config；fixture/dry-run禁止token，live缺值fail closed。
- `structured_logging.py`：JSON logs與registered secret/sensitive-key redaction。
- `lifecycle.py`、`health.py`：reverse-order graceful cleanup與non-sensitive health。
- `contracts.py`：本機Draft 2020-12 registry、fixture loading/validation。
- `models.py`、`ports.py`：framework-neutral snapshots與separate reader/writer protocols。
- `errors.py`、`idempotency.py`：typed failures與fixture operation store。
- `testing.py`：完全記憶體fake Discord client、mapping repository與lifecycle component。

Import package不讀environment、不需要token、不建立network client。只有caller明確呼叫named config loader才解析environment。
