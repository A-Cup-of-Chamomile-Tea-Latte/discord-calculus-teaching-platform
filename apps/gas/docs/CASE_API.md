# Fixture-first public case API

Task 17只提供local fixture API core與ports。沒有deployed endpoint、Sheets/Discord provider、token或真實data。

## Operations

| Operation                                | Input                                | Fixture result                                    |
| ---------------------------------------- | ------------------------------------ | ------------------------------------------------- |
| `GET /health`                            | none                                 | service/mode與`discordGatewayHost:false`          |
| `GET /api/cases/lookup?case=C01-7K4M2Q-0702-1000` | opaque public case number            | `CaseLookupResponse` reduced projection           |
| `GET /api/cases`                         | none                                 | 五筆fixture public summaries；不含Private Support |
| `POST /api/cases/refresh`                | JSON `{ "caseNumber": "..." }`       | explicit `NO_OP`、`polling:false`                 |
| `POST /api/cases/follow-up`              | case number、content、author display | `NOT_CONFIGURED`、`persisted:false` placeholder   |

Missing/malformed case number回`INVALID`；unknown回`NOT_FOUND`；general staff-only回`NOT_PUBLIC`。Private Support對public caller一律表現為`NOT_FOUND`，不確認其存在。

GAS `ContentService` response會額外有application `status` envelope；真正CaseLookup contract是`schemaVersion/requestedCaseNumber/outcome/case/lookedUpAt`。Client不得取得`caseId`、user/Discord ID、verifier hash、token或secret。

## Ports and provider boundary

- `CaseRepository`：future Sheets read/index provider。
- `RefreshRequestProvider`：future explicit Discord/bot refresh request；不能變成polling。
- `FollowUpProvider`：future website/modal-mediated follow-up；anonymous內容必須由bot代貼。
- `CaseAuditSink`：只記`eventType/outcome/route/occurredAt`，不記case number、content、user ID。
- `Clock`：讓lookup/audit timestamp可測試。

目前router只在`FIXTURE_MODE=true`使用fixture providers。Non-fixture但未注入正式provider時回`503 CASE_PROVIDER_NOT_CONFIGURED`，不會默默用fixture data。

Portal的`GasCaseLookupAdapter`實作與fixture adapter相同的`CaseLookupAdapter` interface，但transport必須由future integration顯式注入；repository沒有hard-coded GAS URL。Task 07 CaseLookupResponse只含summary，因此Portal adapter採安全fallback：summary當title、author display視為anonymous、messages為空。完整detail provider仍待Task 32整合決策。

## Request validation and structured errors

- Case number先trim/uppercase/remove harmless whitespace，再套`^[A-Z][A-Z0-9]{1,9}-[0-9]{6}$`。
- POST body必須是JSON object；refresh要求string case number。
- Follow-up要求case number、5–2000字元content與allowlisted author display mode。
- Fixture follow-up不保存內容；所有錯誤不回stack、internal record或provider detail。

## GitHub Pages, redirects, and CORS

Apps Script web app常把`script.google.com`請求redirect至`script.googleusercontent.com`。Browser `fetch`預設會follow redirect，但這不等於CORS一定可用；`ContentService`也不提供一般framework那樣的任意response header控制。

因此：

1. 不在Portal hard-code deployment URL；以injected transport隔離。
2. 不使用`mode: "no-cors"`（會得到opaque response，無法安全驗證JSON）。
3. 正式前在實際GitHub Pages origin做GET/POST/preflight/redirect smoke test。
4. 若GAS CORS不符合需求，使用受控same-origin proxy/edge API，不把secret塞進query string。
5. 不允許把open redirect、JSONP callback或wildcard credentialed CORS當捷徑。

## Rate-limit strategy (documented, not implemented)

- UI debounce只改善UX，不是security control。
- 首選在same-origin edge/proxy依IP/session與route做burst + sustained limits；GAS本身通常看不到可靠client IP。
- GAS可用CacheService + LockService對normalized case number/operation做coarse bucket，但不能當唯一abuse control。
- Lookup、refresh、follow-up分開quota；follow-up最嚴格，連續invalid/not-found也要計數。
- Rate-limit audit只記bucket/outcome/time，不記content或raw identifier；Task 29決定數值、retention與incident response。

## No polling

API只有caller明確觸發的lookup/refresh。Service與Portal client都沒有`setInterval`/`setTimeout`輪詢；future refresh provider只能處理單次request。
