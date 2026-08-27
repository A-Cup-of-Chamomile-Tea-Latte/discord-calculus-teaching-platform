# Portal user journeys

更新日期：2026-08-28

## 加入課程伺服器

1. 使用者先從課程提供的邀請進入 Discord 等候區。
2. 在 Portal 選擇「臺大學生」或「訪客」，填 Discord 使用者名稱（不前綴 `@`）。
3. 學生填 NTU Mail 與班別，聯絡 Gmail 選填；訪客填聯絡 Email 與來訪原因。
4. backend 先以正規化 Email＋Discord username 去重；解析到成員後改綁穩定 Discord user ID，不以學期作 dedup key。
5. Course Manager 找不到成員時保留為「等待加入伺服器」，不拒絕、不刪除。
6. 教學審核者核准／拒絕；系統管理員另可管理審核者、設定、例外與封存。
7. 核准後 Course Manager 套用角色／暱稱並以 Discord 私訊通知。重複申請則私訊「你已經註冊過了呦！」與目前權限。

## 公開提問

1. 學生在 Discord 選擇「數學問題／課務與系統／延伸討論」。
2. 直接發文並附上需要的圖片。
3. Bot 詢問題型、關鍵字與本案 AI 同意。
4. Bot 整理標題、建立案件，並私訊案號與直達連結。
5. 後續對話留在原討論串；結案後重新開啟仍沿用原 thread 與案號。

## 隱密支援

1. 學生從 Discord 指令選單建立隱密支援。
2. Course Manager 建立只讓案件建立者與授權教學團隊看見的空間。
3. 問題、圖片、類型與 AI 同意沿用公開案件流程；差別只有可見度。
4. Bot 私訊以 `-P` 結尾的案號與直達連結。
5. Portal 不收內容或附件，也不另存 Discord 圖片副本。

Production 已提供 `/private open`；實際 ACL、關閉、private dump 與自動刪除仍待白帳號端到端驗收。Portal 只查詢不含內容的最小狀態，不接收案件操作。

## 查詢案件

1. 在首頁或 `/cases/` 輸入完整案號；一般與 `-P` 隱密案號使用同一介面，不要求第二組驗證碼。
2. 回應只包含案號、案件類型、狀態、最後更新、教學團隊是否回覆及 Discord 直達連結。
3. 不回傳題目、對話、作者、附件、班級、AI 選擇或內部 ID。
4. 不存在、無權限或不可用採最小揭露；不列出相似案件，不背景 polling。
5. 主要下一步是「前往 Discord 查看與回覆」。

目前可用 synthetic SQLite 測試 Case ID 狀態查詢。Portal 尚未進入 external staging，也沒有 production hosting；頁面上的「測試中」表示查詢結果可能延遲或不可靠。

## 失敗與恢復

- 送出重複加入申請：回覆既有狀態，不新增資料。
- 重複 Discord interaction：以 interaction／thread identity 冪等，不用問題內容 hash 判定。
- Discord member 尚未出現：保留等待，不刪資料。
- Discord title／archive 延遲：狀態先明確受理，內部 durable worker 最終收斂。
- 動態 adapter 未接線：公開 UI 停用動作，不用 fixture 冒充正式成功。
