# Portal review design system

## Intent

這是一套供課程團隊審查的 UI foundation：先建立資訊層級、可存取性、mobile layout 與 semantic states，再逐頁確認學生文案。視覺採深綠、暖白與燙金重點；警示使用真正的 danger red。沒有採用 Tailwind、component library、大型 template、logo 或 custom illustration。

## Token layers

| Layer           | Examples                                            | Rule                                        |
| --------------- | --------------------------------------------------- | ------------------------------------------- |
| Canvas/surfaces | `--color-canvas`, `--color-surface`                 | 元件不寫死背景色                            |
| Text/borders    | `--color-text`, `--color-border-strong`             | 保持高辨識對比，品牌調整需重新驗證          |
| Action/focus    | `--color-action`, `--color-focus`, `--focus-width`  | Focus 不與 hover 共用，3px outline + offset |
| Semantic states | info/success/warning/danger/neutral bg+border       | 顏色只作輔助；每個狀態都有文字與符號        |
| Typography      | system stack、五級 sizes、body/heading line heights | 不下載 webfont，避免品牌過早定案            |
| Space/radius    | `--space-1`…`--space-7`、三種 radius                | Mobile-first，間距比裝飾更重要              |
| Layout          | content/reading width、touch target                 | 互動目標至少 2.75rem；內容最大寬可換 token  |

## Components

- `SiteHeader` / `SiteFooter`：精實的語意 header/nav/footer；公開版不顯示 mode badge、內部登入或 owner status。
- `Card`：行動選項與摘要；title/eyebrow 可省略。
- `StatusBadge`：五種固定案件狀態，永遠顯示 symbol + Traditional Chinese label。
- `MetaLabel`：visibility 與 author display 前綴，不只顯示 enum。
- `Alert`：info/success/warning/danger，danger 使用 `role=alert`，其他為 status。
- `StatePanel`：loading/empty/error/success；loading 有 `aria-live`/`aria-busy`，error 為 alert。
- `FormField`：label、hint、optional/required、error slot；實際 control 必須用 `aria-describedby` 連到 hint/error。
- `ButtonLink`：primary/secondary/quiet/disabled/external；disabled anchor 移除 href 並退出 tab order。
- `ComponentGallery`：只存在 reviewer artifact 的輕量元件 gallery；public build 移除 `/components/`。

## Keyboard and focus

- 全域 interactive elements 使用 `:focus-visible` 3px focus ring，與 semantic state border 分開。
- Header/footer 使用 native links，表單使用 native controls/button；不以 `div` 模擬按鈕。
- Skip link 在 focus 時出現，並由 BaseLayout 連到 `#main-content`。
- DOM order 就是 mobile reading order；desktop 只改 grid columns，不重排語意順序。

## Mobile-first and responsive rules

- `.grid` 預設單欄，42rem 以上才啟用 auto-fit columns。
- Header navigation 預設另起一列，50rem 以上才移到右側。
- `.shell` 在窄螢幕保留 1rem gutter，寬螢幕增加到 2rem。
- Form controls 永遠滿寬，actions 可 wrap；不設定只適合桌面的 fixed width。

## State communication

| State       | Symbol/word                  | Color role                          |
| ----------- | ---------------------------- | ----------------------------------- |
| Open        | `○ Open · 新案件`            | info border/background only assists |
| Tracked     | `✓ Tracked · 進行中`         | success assists                     |
| Idle        | `↩ Idle · 等待回覆`          | warning assists                     |
| Closed      | `■ Closed · 已結案`          | neutral assists                     |
| Auto Closed | `◇ Auto Closed · 已自動結案` | neutral assists                     |

「重新開啟中」是操作中的暫時文案，「已重新開啟」是時間軸事件；兩者都不是第六個持久狀態。

Loading、empty、error、success 也都有 heading、symbol 及具體下一步，不能只用 spinner／綠紅色。

## Re-theme checklist

1. 只先修改 `tokens.css`，不要逐元件搜尋取代顏色／spacing。
2. 驗證正文、link、button、focus 與各 semantic border/background 對比。
3. 在 320px、375px、768px 及 desktop 檢查 overflow、touch targets、DOM order。
4. 以鍵盤走過 skip link、nav、forms、actions；error summary 能導回欄位。
5. 在 forced colors 與 prefers-reduced-motion 模式檢查內容仍可理解。

## Known integration limits

- Astro compiler/build 已驗證 `.astro` 元件；目前 Portal diagnostics 為 0 errors、0 warnings、0 hints。
- same-origin backend、匿名分 scope session 與 synthetic staging 已完成本機驗證，GAS provider smoke 也已通過。Portal 尚未進入 external staging，沒有 production hosting；系網掛載、institution logo 與 custom domain 均未授權。
- `FormField` 不自動修改 slotted control 的 ARIA；頁面作者必須連結 hint/error IDs，fixture forms tests 已覆蓋這項要求。
