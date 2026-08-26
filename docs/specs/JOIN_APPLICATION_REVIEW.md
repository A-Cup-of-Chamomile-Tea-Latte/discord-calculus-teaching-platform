# 加入申請與 Course Manager 審核

狀態：`V13_DEPLOYMENT_BACKEND_IMPLEMENTED / NOT_DEPLOYED`

更新日期：2026-08-27

## 流程

1. 使用者先加入 Discord 等候區。
2. Portal 收最少必要資料：身份、Discord username，以及學生或訪客的必要欄位。
3. Portal 透過獨立 GAS sender 寄一次六位數 Email 驗證碼；challenge 綁定 session 與 Email，最多五次、10 分鐘失效。
4. 驗證成功後，伺服器端建立或回傳既有申請，進入 Course Manager 佇列。
5. 教學審核者核准、拒絕，或標記為等待加入伺服器。
6. 核准後 Bot 原子地套用 broad course role、班級或訪客角色及暱稱。
7. 審核完成後用 Discord 私訊通知；Email 只負責加入前驗證，不寄審核結果。

## 狀態

- `PENDING_REVIEW`
- `WAITING_FOR_DISCORD_MEMBER`
- `APPROVED`
- `REJECTED`
- `ARCHIVED`

`ARCHIVED` 是可逆 stage，必須保留前一狀態、原因、操作者與時間；清理政策核准前不得物理刪除。

## 去重

- 尚未解析 Discord member 時：正規化 Email＋正規化 Discord username＋身份類型。
- 解析成功後：綁定 stable Discord user ID，username 變更不建立新身份。
- 暫不把學期放入 applicant identity key。
- 重複申請不新增 row；Course Manager 私訊：「你已經註冊過了呦！」並附目前班級／權限。
- 找不到 Discord 成員不是拒絕條件，改為 `WAITING_FOR_DISCORD_MEMBER`。

## 權限

| 能力                     | 教學審核者（TA／教師） | 系統管理員 |
| ------------------------ | ---------------------- | ---------- |
| 查看必要申請欄位         | ✓                      | ✓          |
| 核准／拒絕／等待成員     | ✓                      | ✓          |
| 新增或撤銷審核者         |                        | ✓          |
| 修改設定／例外處理／封存 |                        | ✓          |

Portal 的本機 `staff` 身份代表教學審核者，`admin` 代表系統管理員；這只是 reviewer UI 映射，不是 production authorization。

## 已接線（尚未部署）

- authenticated same-origin join、Email start/verify 與 one-case lookup。
- SQLite schema v13、唯一鍵、transition audit、archive metadata 與 durable outbox。
- Discord guild member resolution、角色／暱稱 orchestration 與 C01–C16 mapping spec。
- Course Manager DM success／duplicate／rejection／waiting copy，以及 reopen success DM。
- `/ops attention-*` 與 `/ops replacement-case` allowlisted 人工接管。

## 尚待 production gate

- owner GAS push 與白帳號收信測試。
- production v6 consistent backup rehearsal、secure Discord mapping preview/receipt。
- 一次明示 v13 deploy authorization；未授權前不 migration、不重啟 service。
