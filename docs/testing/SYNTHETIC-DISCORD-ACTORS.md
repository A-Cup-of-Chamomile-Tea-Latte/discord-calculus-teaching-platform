# Synthetic Discord actors

`bots/common/synthetic.py` 提供完全離線的 student、TA、teacher、webhook-like actor，
以及 fake interaction、thread、read、close、reopen 與結案後新活動事件。所有識別值強制使用
`synthetic_`／`fixture_` 前綴，不能宣稱是真實 Discord 帳號。

這些 doubles 只驗證 domain/service 邏輯，**不等同一般 Discord 使用者帳號**，也不能驗證：

- OAuth 登入、token scope 或真實 session；
- Discord client UI、modal、button、slash-command delivery；
- DM 是否可達、封鎖與隱私設定；
- guild role、channel overwrite、thread ownership 與實際 permission；
- rate limit、Gateway event ordering 或 webhook signature。

上述行為仍需在隔離 test server 使用真人控制的測試帳號進行明確核准的人工測試；本 fixture
不得帶入 112／113／114 server 或真實學生資料。
