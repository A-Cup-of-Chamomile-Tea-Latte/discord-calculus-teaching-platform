# Wireframe text outlines and content inventory

## `/` Home

1. **Skip link**：「跳到主要內容」。
2. **Header**：文字 project mark、主要導覽、原型 mode badge。
3. **Authority notice**：「教材、作業、成績、期限與正式公告請以 NTU COOL 為準」＋回到 NTU COOL 的位置。
4. **Hero copy**：一句說明「找問題進度、選擇提問方式、先了解隱私」。不使用大型插圖。
5. **Primary case search**（首屏／第一主區塊）：label「輸入一般案件編號」、input、查詢 button、格式提示、loading/not-found/error live region。
6. **Ask choices cards**：直接 Discord（推薦給一般討論）、透過網站代送（替代方案）、Private Support（獨立保護）。
7. **Setup & privacy**：加入與設定、暱稱限制、DM privacy。
8. **Status summary**：Fixture mode、最後更新、完整狀態連結。
9. **Footer**：平台邊界與外部返回點。

## `/cases/` Search

- Breadcrumb → H1「查詢一般案件」。
- 說明只查 GENERAL，Private Support 不會出現。
- Search form 與狀態 live region。
- Empty：案件編號示例與「不列出所有案件」。
- Not found / not public：統一訊息。
- Error：明確 refresh，不自動 polling。

## `/cases/[caseNumber]/` General case detail

- Breadcrumb，不在 URL／畫面顯示 internal ID。
- H1 顯示 title；旁列人可讀 case number。
- Status badge（文字＋符號，不只顏色）、最後更新、visibility、author display 說明。
- Latest teaching-team response callout。
- Conversation history：author label、role、時間、reply relation、edited label、attachment metadata；不顯示 Discord snowflake。
- Actions：「重新整理此案件」、「在 Discord 查看討論（placeholder）」。
- Follow-up placeholder：提醒匿名 follow-up 使用網站／modal 代貼。
- NTU COOL authority notice。

## `/join/` Join & setup

- H1、流程三步提示：連結 Discord placeholder → 驗證／班別 → 隱私設定。
- Fields：NTU email、optional Gmail、class、course alias preview、analysis default、rules/privacy acknowledgement。
- Privacy callout：nickname 不隱藏全域資料；停用陌生 DM 建議。
- Submit button 明確寫「建立 fixture 確認（不會送出）」。
- Confirmation panel：不宣稱 email 已寄、server 已加入或資格已核准。

## `/ask/` Ask through portal

- H1 中含「替代方案」；頂部提供「直接在 Discord 發問」。
- Fields：title、question、visibility、author display、analysis permission、attachment metadata placeholder。
- 三概念 inline help，不把 anonymous 與 teaching-staff-only 混同。
- NTU COOL checkbox：正式課務仍以 NTU COOL 為準。
- Confirmation：fixture case number 與下一步；匿名 follow-up 限網站/modal-mediated。

## `/private-support/`

- 高辨識警告：「不會出現在公開案件查詢；預設排除教學分析」。
- 說明誰可見、原型未連正式受保護 backend。
- 最小內容表單，不共用一般案件 case-number receipt。
- Submit：「建立私密 fixture 確認（不會送出）」。
- Confirmation 不提供公開 case number 或 Discord link。

## `/guide/`

- 平台分工（NTU COOL／Discord／Portal）。
- 直接 Discord vs 網站代送 comparison table。
- 作者顯示、visibility、analysis permission 三欄解說。
- course alias `nnmmm` 與 Discord 全域資料限制。
- Private Support、DM privacy、語音不錄音／轉錄、明確匯出／分析界線。

## `/status/`

- 總狀態：Fixture mode / no production services。
- Portal static、Case adapter、Discord、GAS/Sheets、email 分列狀態文字與符號。
- 「最後人工更新」與 fallback；不顯示 secrets、內部 host 或假 SLA。

## Content inventory

| Content item | Owner/source | Used on | Update trigger |
|---|---|---|---|
| NTU COOL authority sentence | Teaching team | Home, detail, ask, guide, footer | 課程政策審查 |
| Case status labels/descriptions | `common.schema.json` + product copy | Search, detail, gallery | Status ADR／schema change |
| Visibility labels | Contracts + privacy copy | Ask, detail, guide | Privacy review |
| Author-display labels | Contracts + privacy copy | Ask, detail, join, guide | Privacy review |
| Analysis permission wording | Consent governance draft | Ask, private, join, guide | Tasks 27/29/31 |
| Direct Discord link | Deployment config | Home, ask, detail, guide | 正式 server 授權 |
| NTU COOL link | Teaching config | Home, guide, detail, footer | 正式 URL 確認 |
| Fixture case data | `fixtures/cases`, `fixtures/messages` | Search, detail, gallery | Deliberate fixture change |
| Private Support warning | Teaching/privacy owners | Home, private, guide | Governance review |
| DM recommendation | Discord privacy guidance | Join, guide | Discord UI/policy change |
| System status labels | Status adapter | Home, status | Service/config change |
| Prototype/mocked notices | Maintainers | All interactive pages | External integration authorization |

## Content constraints

- Student-facing copy uses Traditional Chinese, short sentences and concrete consequences.
- Buttons describe the effect；fixture actions include「不會送出」。
- Error copy avoids blame and never confirms private-case existence.
- No final brand colors, custom illustration, institutional logo or approval claim in Task 09。
