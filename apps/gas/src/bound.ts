import type { CompactMigrationResult } from "./sheets/bootstrap";
import { migrateActiveSpreadsheet } from "./sheets/gas-workbook";
import { queueLabCommand, type LabAction } from "./bridge/commands";
import { GasWorkbookAdapter } from "./sheets/gas-workbook";
import { classifyStatus, digestBody, latestDueSlot } from "./status-digest";

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
    .addSeparator()
    .addItem("資料聯動實驗室", "boundOpenDataLab")
    .addSeparator()
    .addItem("安裝狀態摘要排程…", "boundInstallStatusDigest")
    .addToUi();
}

const LAB_HTML = `<!doctype html>
<html lang="zh-Hant"><head><base target="_top"><style>
body{font:14px/1.55 system-ui,sans-serif;color:#16302b;padding:18px;background:#faf8f2}
h1{font-size:20px;margin:0 0 4px}.badge{display:inline-block;padding:4px 8px;border:1px solid #ad6b12;border-radius:99px;color:#8a4f05;font-weight:700}
p{margin:8px 0 14px}.actions{display:grid;gap:8px}button{padding:10px 12px;text-align:left;border:1px solid #b9c2bd;border-radius:8px;background:white;cursor:pointer}button:hover{border-color:#15594c}
#result{margin-top:14px;padding:10px;background:#eef3f0;border-radius:8px;white-space:pre-wrap}.small{font-size:12px;color:#586762}
</style></head><body><span class="badge">STAGING / SYNTHETIC ONLY</span><h1>資料聯動實驗室</h1>
<p>不操作 Discord、不碰 live DB。每次只會建立一筆固定類型的假命令。</p><div class="actions">
<button onclick="queue('CREATE_BASIC')">建立基本假案件</button>
<button onclick="target('CLOSE_CASE')">關閉指定假案件</button>
<button onclick="target('REOPEN_CASE')">重開指定假案件</button>
<button onclick="queue('REPLAY_LAST')">重送上一筆假命令</button>
<button onclick="queue('STALE_VERSION_TEST')">提交 stale-version 測試</button>
<button onclick="queue('BAD_CHECKSUM_TEST')">提交 bad-checksum 測試</button></div>
<div id="result">尚未建立命令。</div><p class="small">下一步：本機執行 discord-data-bridge fetch --once --dry-run</p>
<script>function target(a){const r=prompt('輸入 TST- 開頭的假案件編號');if(r)queue(a,r)}function queue(a,t=null){document.getElementById('result').textContent='建立中…';google.script.run.withSuccessHandler(r=>document.getElementById('result').textContent='已建立 '+r.jobRef+'\n狀態：'+r.status).withFailureHandler(e=>document.getElementById('result').textContent='未建立：'+e.message).boundQueueDataLabCommand(a,t)}</script>
</body></html>`;

export function boundOpenDataLab(): void {
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutput(LAB_HTML).setTitle("資料聯動實驗室"),
  );
}

export function boundQueueDataLabCommand(
  action: LabAction,
  targetCaseRef: string | null,
) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("COMMAND_LOCK_UNAVAILABLE");
  try {
    return queueLabCommand(
      new GasWorkbookAdapter(SpreadsheetApp.getActiveSpreadsheet()),
      action,
      targetCaseRef,
      new Date().toISOString(),
    );
  } finally {
    lock.releaseLock();
  }
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

const DIGEST_HANDLER = "boundStatusDigestDispatcher";

export function boundInstallStatusDigest(): { installed: true } | { cancelled: true } {
  const ui = SpreadsheetApp.getUi();
  const decision = ui.alert(
    "安裝狀態摘要排程",
    "將建立每 5 分鐘一次的輕量檢查；只有 07:00、13:30、19:00 三個時段會寄一封簡潔摘要。收件人需先設於 Script Property：STATUS_EMAIL_RECIPIENTS。",
    ui.ButtonSet.YES_NO,
  );
  if (decision !== ui.Button.YES) return { cancelled: true };
  const properties = PropertiesService.getScriptProperties();
  properties.setProperty(
    "STATUS_SPREADSHEET_ID",
    SpreadsheetApp.getActiveSpreadsheet().getId(),
  );
  for (const trigger of ScriptApp.getProjectTriggers()) {
    if (trigger.getHandlerFunction() === DIGEST_HANDLER) ScriptApp.deleteTrigger(trigger);
  }
  ScriptApp.newTrigger(DIGEST_HANDLER).timeBased().everyMinutes(5).create();
  return { installed: true };
}

export function boundStatusDigestDispatcher(): { status: string; slot?: string } {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1_000)) return { status: "LOCKED" };
  try {
    const now = new Date();
    const slot = latestDueSlot(now);
    if (!slot) return { status: "NO_SLOT" };
    const properties = PropertiesService.getScriptProperties();
    const receiptKey = `STATUS_DIGEST_${slot}`;
    if (properties.getProperty(receiptKey)) return { status: "ALREADY_ATTEMPTED", slot };
    const recipients = properties.getProperty("STATUS_EMAIL_RECIPIENTS");
    const spreadsheetId = properties.getProperty("STATUS_SPREADSHEET_ID");
    if (!recipients || !spreadsheetId) return { status: "NOT_CONFIGURED", slot };
    properties.setProperty(receiptKey, "ATTEMPTING");
    const decision = classifyStatus(
      new GasWorkbookAdapter(SpreadsheetApp.openById(spreadsheetId)),
      now,
    );
    const label = slot.slice(-4, -2) + ":" + slot.slice(-2);
    try {
      MailApp.sendEmail(
        recipients,
        `[微積分 Bot] ${decision.subjectState}｜${label}`,
        digestBody(decision),
      );
      properties.setProperty(receiptKey, "PROVIDER_ACCEPTED");
      return { status: "PROVIDER_ACCEPTED", slot };
    } catch (error) {
      properties.setProperty(receiptKey, "ATTEMPTED_FAILED");
      throw error;
    }
  } finally {
    lock.releaseLock();
  }
}
