# Low-fidelity portal design system

## Intent

這是一套刻意低擬真的 UI foundation：先建立資訊層級、可存取性、mobile layout 與 semantic states，再由後續品牌決策替換 tokens。沒有採用 Tailwind、component library、大型 template、logo 或 custom illustration。

## Token layers

| Layer | Examples | Rule |
|---|---|---|
| Canvas/surfaces | `--color-canvas`, `--color-surface` | 元件不寫死背景色 |
| Text/borders | `--color-text`, `--color-border-strong` | 保持高辨識對比，品牌調整需重新驗證 |
| Action/focus | `--color-action`, `--color-focus`, `--focus-width` | Focus 不與 hover 共用，3px outline + offset |
| Semantic states | info/success/warning/danger/neutral bg+border | 顏色只作輔助；每個狀態都有文字與符號 |
| Typography | system stack、五級 sizes、body/heading line heights | 不下載 webfont，避免品牌過早定案 |
| Space/radius | `--space-1`…`--space-7`、三種 radius | Mobile-first，間距比裝飾更重要 |
| Layout | content/reading width、touch target | 互動目標至少 2.75rem；內容最大寬可換 token |

## Components

- `SiteHeader` / `SiteFooter`：語意 header/nav/footer、可注入 base-safe links、fixture mode 標籤。
- `Card`：行動選項與摘要；title/eyebrow 可省略。
- `StatusBadge`：五種固定案件狀態，永遠顯示 symbol + Traditional Chinese label。
- `MetaLabel`：visibility 與 author display 前綴，不只顯示 enum。
- `Alert`：info/success/warning/danger，danger 使用 `role=alert`，其他為 status。
- `StatePanel`：loading/empty/error/success；loading 有 `aria-live`/`aria-busy`，error 為 alert。
- `FormField`：label、hint、optional/required、error slot；實際 control 必須用 `aria-describedby` 連到 hint/error。
- `ButtonLink`：primary/secondary/quiet/disabled/external；disabled anchor 移除 href 並退出 tab order。
- `ComponentGallery`：只使用 fixture copy 的輕量 gallery，Task 11 會掛到 `/components/`。

## Keyboard and focus

- 全域 interactive elements 使用 `:focus-visible` 3px focus ring，與 semantic state border 分開。
- Header/footer 使用 native links，表單使用 native controls/button；不以 `div` 模擬按鈕。
- Skip link 在 focus 時出現；Task 11 BaseLayout 必須把它連到 `#main-content`。
- DOM order 就是 mobile reading order；desktop 只改 grid columns，不重排語意順序。

## Mobile-first and responsive rules

- `.grid` 預設單欄，42rem 以上才啟用 auto-fit columns。
- Header navigation 預設另起一列，50rem 以上才移到右側。
- `.shell` 在窄螢幕保留 1rem gutter，寬螢幕增加到 2rem。
- Form controls 永遠滿寬，actions 可 wrap；不設定只適合桌面的 fixed width。

## State communication

| State | Symbol/word | Color role |
|---|---|---|
| Open | `○ 待處理` | info border/background only assists |
| Waiting | `↩ 等待學生補充` | warning assists |
| Answered | `✓ 已回覆` | success assists |
| Escalated | `↑ 已升級處理` | danger assists |
| Closed | `■ 已結案` | neutral assists |

Loading、empty、error、success 也都有 heading、symbol 及具體下一步，不能只用 spinner／綠紅色。

## Re-theme checklist

1. 只先修改 `tokens.css`，不要逐元件搜尋取代顏色／spacing。
2. 驗證正文、link、button、focus 與各 semantic border/background 對比。
3. 在 320px、375px、768px 及 desktop 檢查 overflow、touch targets、DOM order。
4. 以鍵盤走過 skip link、nav、forms、actions；error summary 能導回欄位。
5. 在 forced colors 與 prefers-reduced-motion 模式檢查內容仍可理解。

## Known prototype limits

- Astro compiler/build 已驗證 `.astro` 元件；目前 Portal diagnostics 為 0 errors、0 warnings、0 hints。
- 尚未做 final branding、dark theme、institution logo 或 custom domain。
- `FormField` 不自動修改 slotted control 的 ARIA；頁面作者必須連結 hint/error IDs，fixture forms tests 已覆蓋這項要求。
