# Portal synthetic staging host contract

這不是 Nginx、Caddy 或 Apache 設定檔。主機 owner 必須先提供一個 root-owned、不可由 `ding` 修改的 executable adapter；installer 不猜測主機使用哪一種 proxy。

Adapter 接受第一個參數 `check`、`enable` 或 `disable`，其後固定收到：

```text
--origin https://staging.example
--base-path /portal-staging
--upstream http://127.0.0.1:18081
```

- `check`：只驗證 HTTPS origin、憑證、路由可用性與設定語法，不 reload、不改設定。
- `enable`：以 atomic／validated 方式啟用 static 與 API 的同一路由，保留原始 `Host`，並把唯一 canonical client IP 放入單一 `X-Forwarded-For` header；成功後才 reload。
- `disable`：撤除本 staging 路由並安全 reload；必須 idempotent。

Proxy 不得把 `X-Forwarded-For` 原值直接串接下去。它必須覆寫為 proxy 所見的單一 client IP。上游僅監聽 loopback，且不能路由到 production Portal、Discord services、`/var/lib/calculus-discord` 或 `/etc/calculus-discord`。

任何 action 回傳非零，installer 都停止。Public smoke 失敗時會先呼叫 `disable`，再停止 staging service；不會碰 production symlink、SQLite 或三個 v13 services。
