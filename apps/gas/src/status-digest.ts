import type { SheetRecord, WorkbookPort } from "./sheets/bootstrap";

export type DigestLevel = "NORMAL" | "ATTENTION" | "CRITICAL";

export interface DigestDecision {
  level: DigestLevel;
  subjectState: "正常" | "注意" | "異常";
  action: string;
  botState: string;
  syncState: string;
  caseState: string;
  lastUpdated: string;
  safeErrorCode: string | null;
}

function rows(
  workbook: WorkbookPort,
  sheetName: string,
  key: string,
): SheetRecord[] {
  const sheet = workbook.getSheet(sheetName);
  if (!sheet) return [];
  return sheet
    .getColumnValues(key)
    .filter(Boolean)
    .map((value) => sheet.getRowByPrimaryKey(key, value))
    .filter((row): row is SheetRecord => row !== null);
}

function ageMinutes(timestamp: unknown, now: Date): number {
  const parsed = Date.parse(String(timestamp ?? ""));
  return Number.isFinite(parsed) ? (now.getTime() - parsed) / 60_000 : Infinity;
}

export function classifyStatus(
  workbook: WorkbookPort,
  now: Date,
): DigestDecision {
  const operations = rows(workbook, "Operations", "operationKey");
  const overview = rows(workbook, "Overview", "metricKey");
  const bridge = operations.find((row) => row.operationKey === "data-bridge");
  const freshest = operations.reduce<SheetRecord | null>((current, row) => {
    if (!current) return row;
    return Date.parse(String(row.checkedAt)) >
      Date.parse(String(current.checkedAt))
      ? row
      : current;
  }, null);
  const age = ageMinutes(bridge?.lastHeartbeatAt ?? freshest?.checkedAt, now);
  const explicitCritical = operations.some((row) =>
    ["DOWN", "CRITICAL", "PERMANENT_FAILURE", "OAUTH_REVOKED"].includes(
      String(row.status),
    ),
  );
  const explicitAttention = operations.some((row) =>
    ["DEGRADED", "ATTENTION", "RETRYABLE_FAILURE"].includes(String(row.status)),
  );
  const level: DigestLevel =
    explicitCritical || age > 30
      ? "CRITICAL"
      : explicitAttention || age > 15
        ? "ATTENTION"
        : "NORMAL";
  const open = overview.find((row) => row.metricKey === "cases.open");
  const hasCases = Number(open?.metricValue ?? 0) > 0;
  const safeCode =
    operations.find((row) => row.safeErrorCode)?.safeErrorCode ?? null;
  return {
    level,
    subjectState:
      level === "NORMAL" ? "正常" : level === "ATTENTION" ? "注意" : "異常",
    action:
      level === "NORMAL"
        ? "無"
        : "- Bot 已超過預期時間沒有回報，請登入主機檢查。",
    botState: level === "CRITICAL" ? "有異常" : "正常",
    syncState: age > 15 ? "延遲" : "正常",
    caseState: hasCases ? "目前有待處理案件。" : "案件目前無需特別處理",
    lastUpdated: String(
      bridge?.lastHeartbeatAt ?? freshest?.checkedAt ?? "沒有資料",
    ),
    safeErrorCode: safeCode === null ? null : String(safeCode),
  };
}

export function digestBody(decision: DigestDecision): string {
  const lines = [
    `整體狀態：${decision.subjectState}`,
    "",
    "需要你處理：",
    decision.action,
    "",
    "最近狀況：",
    `- Discord Bot ${decision.botState}`,
    `- 資料同步${decision.syncState}`,
    `- ${decision.caseState}`,
    "",
    "資料時間：",
    `最後更新 ${decision.lastUpdated}`,
  ];
  if (decision.level !== "NORMAL" && decision.safeErrorCode)
    lines.push("", `安全錯誤代碼：${decision.safeErrorCode}`);
  return lines.join("\n");
}

export function latestDueSlot(now: Date): string | null {
  const date = Utilities.formatDate(now, "Asia/Taipei", "yyyy-MM-dd");
  const hhmm = Utilities.formatDate(now, "Asia/Taipei", "HHmm");
  const slot = ["0700", "1330", "1900"].filter((value) => value <= hhmm).at(-1);
  return slot ? `${date}:${slot}` : null;
}
