# 尚未部署：現況、關卡與安全停止點

## 一句話現況

本儲存庫是可 build、test 與 fixture-demo 的本機原型，**不是已部署的課程服務**。沒有建立 GitHub remote/Pages site、Apps Script cloud project、正式 Sheets、Discord applications/server connection、OAuth registration 或 email provider。

## 已完成的是什麼？

- Astro static Portal、14 routes、fixture case lookup/forms、base-path verifier 與本機 build。
- GAS/Sheets pure logic、schema/bootstrap/case API/activation/email mocks 與 local bundle。
- 多 bot 責任分離、fixture transports/services、匿名 modal 與 Private Support policy skeleton。
- 明確選定 thread 的 raw export、consent/anonymizer 與 dry-run/CSV/mock batch importer。
- 跨元件 contracts、fictional fixtures、品質檢查與非部署 CI。

## 仍是 mock、stub 或未驗證的部分

| 領域                   | 現況                                             | 未來最少需要                                                                                   |
| ---------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Portal 正式後端        | fixture 直讀；GAS transport 只有 adapter/test    | AuthN/AuthZ、same-origin/proxy or reviewed CORS、rate limit、最小化 response                   |
| GitHub Pages           | workflow 有 manual deploy gate，但未 dispatch    | 確認 owner/repo/visibility/base path、privacy review、Pages public-vs-course-only 決策         |
| Discord                | fixture services；live reader fail closed        | 建立分離 applications/tokens、核准 intents/permissions、rate-limit/retry/audit technical spike |
| Private Support        | backend-only fixture representation              | 驗證正式 restricted mechanism、participants sync、permission regression 與 break-glass         |
| GAS / Sheets           | in-memory/mock adapters 與 local build           | 正式 owner/account、deployment model、Properties secrets、locking/quota/access/backup          |
| Email / OAuth          | mock delivery 與 conceptual boundary             | provider/registration、callback/session/CSRF、abuse controls、客製正式文案                     |
| Export / anonymization | fixture/local CLI；regex + known-value redaction | 管理者身分、durable audit/consent snapshot、retention/deletion、human approval gate            |
| Sheets importer        | dry-run/CSV/mock；production adapter fail closed | 受授權 endpoint、authentication、idempotency storage、quota/retry 實測                         |

## 不可當作「純技術步驟」跳過的關卡

1. 授課教師／課程 owner 同意試用範圍與人員責任。
2. 隱私與資料治理審查：告知、同意、撤回、保留、刪除、Private Support 與附件。
3. 決定 public case lookup 的驗證與暴露範圍；GitHub Pages 的 internet-public 特性不能當作 course-only access control。
4. 核准多 bot 權限矩陣、Discord intents 與 Private Support 具體機制。
5. 確認 GAS deployed-as-owner 的身分、CORS、quota、locking、Sheets sharing 與 incident owner。
6. 完成威脅模型中的 production blockers，並與 Task 32 integration plan / Task 33 go-no-go 交叉審閱。
7. 每個外部狀態變更都需個別授權：create remote、push、Pages enable/dispatch、GAS create/deploy、OAuth/bot registration、email/Discord live test。

## GitHub Pages 特別說明

`.github/workflows/pages.yml` 的 push job 只 build/test/verify/upload artifact；只有手動 `workflow_dispatch` 且 `deploy=true` 才存在 deploy 路徑。這是安全關卡，不是部署授權。現階段不可執行該 dispatch。詳細預備文件見 `apps/portal/docs/GITHUB_PAGES.md`。

## 發現不當資料時

- 立即停止 demo/import/export，不把原文貼入 issue、chat 或報告。
- 記錄受影響的資料類別、位置與時間，不複製敏感值。
- 封鎖或移離該 local artifact；若已公開，交由授權 owner unpublish/revoke。
- 保留必要的 metadata-only audit，再依治理流程決定刪除與通知。

本文件不是 legal approval 或 production checklist sign-off。它的用途是讓審查者清楚看見「還沒有做」的邊界。
