import type { CompactMigrationResult } from "./sheets/bootstrap";
import { migrateActiveSpreadsheet } from "./sheets/gas-workbook";

const MENU_NAME = "微積分模組管理";

function summarize(result: CompactMigrationResult): string {
  if (result.blockers.length > 0) {
    return [
      "為避免誤刪資料，遷移已停止。請先處理以下項目：",
      ...result.blockers.map((blocker) => `• ${blocker}`),
    ].join("\n");
  }
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
    .addItem("檢查精簡資料庫遷移（不修改）", "boundCompactDatabaseDryRun")
    .addSeparator()
    .addItem("套用精簡資料庫遷移…", "boundCompactDatabaseApply")
    .addToUi();
}

export function boundCompactDatabaseDryRun(): CompactMigrationResult {
  const result = migrateActiveSpreadsheet(true);
  const ui = SpreadsheetApp.getUi();
  ui.alert("精簡資料庫遷移檢查", summarize(result), ui.ButtonSet.OK);
  return result;
}

export function boundCompactDatabaseApply():
  CompactMigrationResult | { cancelled: true } {
  const preview = migrateActiveSpreadsheet(true);
  const ui = SpreadsheetApp.getUi();
  if (preview.blockers.length > 0) {
    ui.alert("精簡資料庫遷移已停止", summarize(preview), ui.ButtonSet.OK);
    return preview;
  }
  if (!preview.changed) {
    ui.alert("精簡資料庫", summarize(preview), ui.ButtonSet.OK);
    return preview;
  }
  const decision = ui.alert(
    "確認套用精簡資料庫遷移",
    `${summarize(preview)}\n\n只會刪除確認為空、且名稱完全相符的舊受管分頁；任何舊分頁有資料時，整個遷移都會停止。`,
    ui.ButtonSet.YES_NO,
  );
  if (decision !== ui.Button.YES) return { cancelled: true };
  const result = migrateActiveSpreadsheet(false);
  ui.alert("精簡資料庫遷移已套用", summarize(result), ui.ButtonSet.OK);
  return result;
}
