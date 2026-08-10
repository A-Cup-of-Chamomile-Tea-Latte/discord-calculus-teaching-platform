import type { BootstrapResult } from "./sheets/bootstrap";
import { bootstrapActiveSpreadsheet } from "./sheets/gas-workbook";

const MENU_NAME = "微積分模組管理";

function summarize(result: BootstrapResult): string {
  if (!result.changed) return "資料表結構已是最新版，沒有需要套用的變更。";
  const preview = result.actions
    .slice(0, 12)
    .map((action) => `${action.type}: ${action.sheet}`)
    .join("\n");
  const remaining = result.actions.length - 12;
  return `${result.actions.length} 項變更：\n${preview}${
    remaining > 0 ? `\n…以及另外 ${remaining} 項` : ""
  }`;
}

export function onOpen(): void {
  SpreadsheetApp.getUi()
    .createMenu(MENU_NAME)
    .addItem("檢查資料表結構（不修改）", "boundBootstrapSheetsDryRun")
    .addSeparator()
    .addItem("套用資料表結構…", "boundBootstrapSheetsApply")
    .addToUi();
}

export function boundBootstrapSheetsDryRun(): BootstrapResult {
  const result = bootstrapActiveSpreadsheet(true);
  const ui = SpreadsheetApp.getUi();
  ui.alert("資料表結構檢查", summarize(result), ui.ButtonSet.OK);
  return result;
}

export function boundBootstrapSheetsApply():
  BootstrapResult | { cancelled: true } {
  const preview = bootstrapActiveSpreadsheet(true);
  const ui = SpreadsheetApp.getUi();
  if (!preview.changed) {
    ui.alert("資料表結構", summarize(preview), ui.ButtonSet.OK);
    return preview;
  }
  const decision = ui.alert(
    "確認套用資料表結構",
    `${summarize(preview)}\n\n只會建立缺少的分頁、追加缺少的欄位，並更新受管 schema metadata。`,
    ui.ButtonSet.YES_NO,
  );
  if (decision !== ui.Button.YES) return { cancelled: true };
  const result = bootstrapActiveSpreadsheet(false);
  ui.alert("資料表結構已套用", summarize(result), ui.ButtonSet.OK);
  return result;
}
