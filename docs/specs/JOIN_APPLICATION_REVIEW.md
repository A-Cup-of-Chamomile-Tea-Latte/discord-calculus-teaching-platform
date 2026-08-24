# 加入申請與 Course Manager 審核

狀態：`PORTAL_MODEL_READY / BACKEND_NOT_CONNECTED`

更新日期：2026-08-24

## 流程

1. 使用者先加入 Discord 等候區。
2. Portal 收最少必要資料：身份、Discord username，以及學生或訪客的必要欄位。
3. 伺服器端建立或回傳既有申請，進入 Course Manager 佇列。
4. 教學審核者核准、拒絕，或標記為等待加入伺服器。
5. 核准後 Bot 原子地套用 broad course role、班級或訪客角色及暱稱。
6. 審核完成後只用 Discord 私訊通知，不寄 Email。

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

## 待接線

- authenticated same-origin submission endpoint 與 CSRF／rate limit。
- SQLite migration、唯一鍵、transition audit 與 archive metadata。
- Discord guild member resolution、角色／暱稱 transaction orchestration 與 reconciliation。
- Course Manager DM success／duplicate／rejection／waiting copy。
- 失敗重試與 manual-attention 安全摘要。
