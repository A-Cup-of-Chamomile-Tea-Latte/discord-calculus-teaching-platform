# User fixtures

本目錄只含虛構使用者、身份、membership、consent 與啟動碼 lifecycle records；不得對應真實學生。

`activation-codes.json` 不含可輸入的明文啟動碼、email 或 Discord ID。Task 18 新增的綁定值與 idempotency key 只以固定假資料 fingerprint 表示；permission profile 則明列 fixture 預期授予的最小權限。

`verified-emails.json` 以 Amber 示範 institutional 與偏好 contact 是兩筆各自驗證的 records。所有地址仍使用 `example.com`，`INSTITUTIONAL` 只是 fixture 類型，不代表真實 NTU 網域或選課證明。
