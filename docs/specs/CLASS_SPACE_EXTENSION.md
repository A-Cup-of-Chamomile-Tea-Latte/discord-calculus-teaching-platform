# 班級專屬空間擴張規格

狀態：`PROPOSED_ON_DEMAND`。本文件只定義可審核的擴張方式；目前不建立 Discord category、channel、role 或 permission。

## 決策摘要

若個別班級助教需要班級專屬討論區，採「依需求開設」，不預先建立 C01–C16 全套頻道。

- 一個受控的 `CLASS SPACES` category。
- 每個已核准班級最多一個 Forum，例如 `c01-class-space`。
- Class role 決定學生可見性；該班 TA 與全域 Staff 可見。
- Module 只保留為後端分類屬性，不用 Module role 取代 Class role。
- TA 可以提出開設申請與管理貼文／討論串，但不直接取得全伺服器 `MANAGE_CHANNELS`。

Forum 適合持續數日的課程討論，也可透過 role 限制存取。Discord 的 permission overwrite 可在 channel 層級指定 role 或 member；自動化程式也能在明確授權下建立 channel、設定權限與指派 role。

參考：

- [Discord Forum Channels FAQ](https://support.discord.com/hc/en-us/articles/6208479917079-Forum-Channels-FAQ)
- [Discord Permissions](https://docs.discord.com/developers/topics/permissions)
- [Discord Server and Channel Management](https://docs.discord.com/developers/platform/server-and-channel-management)

## 開設流程

```text
TA 申請
  → bot 驗證 TA 與 Class assignment
  → 管理員預覽 channel 名稱、對象與 permissions
  → 管理員核准
  → bot 以 allowlisted template 建立
  → 寫入 idempotency key、Discord resource ID 與 audit record
```

建議生命週期：`REQUESTED → PREVIEWED → APPROVED → PROVISIONED → ARCHIVED → DISABLED`。

重複申請同一學期、同一 Class 時，系統必須回傳既有資源，不得再建第二個 Forum。學期結束時先封存、確認匯出與存取結果，再停用或移除由系統建立的資源。

## 權限模板

| Actor                       | View | Post／Reply |     管理貼文 | 修改 channel permissions |
| --------------------------- | ---: | ----------: | -----------: | -----------------------: |
| `@everyone`／其他 Class     |   否 |          否 |           否 |                       否 |
| 該班 Class role             |   是 |          是 |           否 |                       否 |
| 該班 TA Lecturer／TA Grader |   是 |          是 |           是 |                       否 |
| Staff／Administrator        |   是 |          是 |           是 |         僅 Administrator |
| Course Assistant            |   是 |      必要時 | 依核准 scope | 僅 template provisioning |
| Dump Bot                    |   是 |          否 |           否 |                       否 |

實際套用前必須用 resolved member 做權限模擬，至少涵蓋：該班學生、其他班學生、該班 TA、其他班 TA、Staff、Guest 與 bot。

## 容量與命名

Discord 目前的公開上限包含每伺服器 500 個 channel、50 個 category、每 category 50 個 channel，以及 250 個 role。即使 C01–C16 全部開設也遠低於 channel 上限；採依需求建立主要是降低管理與權限錯配，不是容量不足。

參考：[Discord Account, Server and Channel Caps](https://support.discord.com/hc/en-us/articles/33694251638295-Discord-Account-Caps-Server-Caps-and-More)

Canonical name：`c{classCode}-class-space`，其中 `{classCode}` 為兩位數，例如 `c01-class-space`。

## 審核閘門

下列事項仍須人工核准後才能執行：

1. 是否啟用 `CLASS SPACES` category。
2. 哪些 Class 首批開設。
3. TA 可用的 moderation 權限細節。
4. 學期末封存、匯出與刪除政策。
5. Bot 的最小 Discord permission scope 與 rollback rehearsal。
