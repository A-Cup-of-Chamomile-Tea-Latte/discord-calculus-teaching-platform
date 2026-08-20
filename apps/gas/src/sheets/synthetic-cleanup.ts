import { canonicalJson } from "../bridge/service";
import type { SheetPort, SheetRecord, WorkbookPort } from "./bootstrap";
import { SHEETS_SCHEMA_VERSION, SHEET_SCHEMAS } from "./schema";

const CLEANUP_SCOPES = [
  "Overview",
  "CaseBoard",
  "Operations",
  "History",
  "_CommandInbox",
  "_EmailOutbox",
  "_SyncState",
  "_Artifacts",
] as const;

type CleanupScope = (typeof CLEANUP_SCOPES)[number];
type CountMap = Record<CleanupScope, number>;
type Sha256 = (value: string) => string;

interface CleanupCandidate {
  scope: CleanupScope;
  primaryKey: string;
  value: string;
  record: SheetRecord;
}

interface CleanupPlanInternal {
  candidates: CleanupCandidate[];
  removableRows: CountMap;
  retainedProtectedRows: CountMap;
  preservedUnknownRows: CountMap;
  totalRemovable: number;
  totalRetainedProtected: number;
  totalPreservedUnknown: number;
  syncSourceVersion: number | null;
  confirmationNonce: string | null;
  blockers: string[];
}

export interface SyntheticCleanupPreview {
  status: "PREVIEW" | "NO_OP" | "BLOCKED";
  schemaVersion: string;
  removableRows: CountMap;
  retainedProtectedRows: CountMap;
  preservedUnknownRows: CountMap;
  totalRemovable: number;
  totalRetainedProtected: number;
  totalPreservedUnknown: number;
  syncSourceVersion: number | null;
  confirmationNonce: string | null;
  blockers: string[];
  safeResultCode: "CLEANUP_PREVIEW_READY" | "CLEANUP_NOOP" | "CLEANUP_BLOCKED";
}

export interface SyntheticCleanupApplyResult {
  status: "APPLIED" | "NO_OP";
  schemaVersion: string;
  deletedRows: CountMap;
  totalDeleted: number;
  retainedProtectedRows: CountMap;
  totalRetainedProtected: number;
  preservedUnknownRows: CountMap;
  totalPreservedUnknown: number;
  safeResultCode: "CLEANUP_APPLIED" | "CLEANUP_NOOP";
}

function emptyCounts(): CountMap {
  return Object.fromEntries(
    CLEANUP_SCOPES.map((scope) => [scope, 0]),
  ) as CountMap;
}

function text(record: SheetRecord, key: string): string {
  return String(record[key] ?? "");
}

function isFalse(value: unknown): boolean {
  return (
    value === false || value === 0 || String(value).toLowerCase() === "false"
  );
}

function isSynthetic(scope: CleanupScope, record: SheetRecord): boolean {
  switch (scope) {
    case "Overview":
      return (
        ["cases.open", "cases.closed"].includes(text(record, "metricKey")) &&
        text(record, "status") === "STAGING" &&
        text(record, "sourceReceipt") === "STAGING-SQLITE"
      );
    case "CaseBoard":
      return (
        text(record, "schemaVersion") === SHEETS_SCHEMA_VERSION &&
        text(record, "caseNumber").startsWith("TST-") &&
        text(record, "assignedAlias") === "SYN-LAB-TA" &&
        isFalse(record.analysisEligible)
      );
    case "Operations":
      return (
        text(record, "schemaVersion") === SHEETS_SCHEMA_VERSION &&
        text(record, "operationKey") === "data-bridge" &&
        text(record, "service") === "calculus-data-bridge" &&
        text(record, "component") === "projection-outbox" &&
        text(record, "mode") === "SYNTHETIC_ONLY"
      );
    case "History":
      return (
        text(record, "schemaVersion") === SHEETS_SCHEMA_VERSION &&
        text(record, "subjectRef").startsWith("TST-") &&
        text(record, "summaryCode").startsWith("SYNTHETIC_CASE_") &&
        ["LOCAL_FIXTURE", "CLOUD_COMMAND"].includes(text(record, "source"))
      );
    case "_CommandInbox":
      return false;
    case "_SyncState":
      return (
        text(record, "schemaVersion") === SHEETS_SCHEMA_VERSION &&
        text(record, "syncKey") === "phase2b.local-projection" &&
        text(record, "direction") === "LOCAL_TO_CLOUD" &&
        text(record, "sourceName") === "staging.sqlite3" &&
        Number.isInteger(Number(record.sourceVersion)) &&
        Number(record.sourceVersion) > 0 &&
        /^[a-f0-9]{64}$/i.test(text(record, "sourceChecksum")) &&
        text(record, "status") === "SUCCESS"
      );
    case "_Artifacts":
      return false;
    case "_EmailOutbox":
      return false;
  }
}

function isProtectedSyntheticReceipt(
  scope: CleanupScope,
  record: SheetRecord,
): boolean {
  if (scope !== "_CommandInbox") return false;
  return (
    text(record, "schemaVersion") === SHEETS_SCHEMA_VERSION &&
    text(record, "jobRef").startsWith("CMD-TST-") &&
    text(record, "payloadRef").startsWith("fixture://") &&
    text(record, "idempotencyKey").startsWith("phase2b:") &&
    ["COMPLETED", "REJECTED"].includes(text(record, "status"))
  );
}

function buildPlan(
  workbook: WorkbookPort,
  sha256: Sha256,
): CleanupPlanInternal {
  const candidates: CleanupCandidate[] = [];
  const removableRows = emptyCounts();
  const retainedProtectedRows = emptyCounts();
  const preservedUnknownRows = emptyCounts();
  const blockers: string[] = [];
  let syncReceipt: CleanupCandidate | null = null;

  for (const scope of CLEANUP_SCOPES) {
    const definition = SHEET_SCHEMAS.find(
      (candidate) => candidate.name === scope,
    );
    if (!definition) throw new Error("CLEANUP_SCHEMA_MISSING");
    const sheet = workbook.getSheet(scope);
    if (!sheet) throw new Error("CLEANUP_SHEET_MISSING");
    const rows = sheet.getRows();
    if (!sheet.getHeaders().includes(definition.primaryKey)) {
      blockers.push(`CLEANUP_PRIMARY_KEY_HEADER_MISSING_${scope}`);
      preservedUnknownRows[scope] += rows.length;
      continue;
    }
    if (sheet.hasDataFormulas()) {
      blockers.push(`CLEANUP_FORMULA_ROWS_REFUSED_${scope}`);
      preservedUnknownRows[scope] += rows.length;
      continue;
    }
    const keys = rows.map((record) => text(record, definition.primaryKey));
    if (keys.some((value) => value === "")) {
      blockers.push(`CLEANUP_BLANK_PRIMARY_KEY_${scope}`);
      preservedUnknownRows[scope] += rows.length;
      continue;
    }
    if (new Set(keys).size !== keys.length) {
      blockers.push(`CLEANUP_DUPLICATE_PRIMARY_KEY_${scope}`);
      preservedUnknownRows[scope] += rows.length;
      continue;
    }
    for (const record of rows) {
      const value = text(record, definition.primaryKey);
      if (isSynthetic(scope, record)) {
        const candidate: CleanupCandidate = {
          scope,
          primaryKey: definition.primaryKey,
          value,
          record,
        };
        if (scope === "_SyncState") {
          syncReceipt = candidate;
        } else {
          candidates.push(candidate);
          removableRows[scope] += 1;
        }
      } else if (isProtectedSyntheticReceipt(scope, record)) {
        retainedProtectedRows[scope] += 1;
      } else {
        preservedUnknownRows[scope] += 1;
      }
    }
  }

  const syncSourceVersion = syncReceipt
    ? Number(syncReceipt.record.sourceVersion)
    : null;
  const totalRemovable = candidates.length;
  const totalPreservedUnknown = Object.values(preservedUnknownRows).reduce(
    (total, count) => total + count,
    0,
  );
  const totalRetainedProtected = Object.values(retainedProtectedRows).reduce(
    (total, count) => total + count,
    0,
  );
  if (totalRemovable > 0 && !syncReceipt)
    blockers.push("SYNTHETIC_SYNC_RECEIPT_REQUIRED");
  const noncePayload = candidates
    .map((candidate) => ({
      scope: candidate.scope,
      primaryKey: candidate.primaryKey,
      value: candidate.value,
      record: candidate.record,
    }))
    .sort((left, right) =>
      `${left.scope}\n${left.value}`.localeCompare(
        `${right.scope}\n${right.value}`,
      ),
    );
  const confirmationNonce =
    totalRemovable > 0 && blockers.length === 0
      ? sha256(
          canonicalJson({
            schemaVersion: SHEETS_SCHEMA_VERSION,
            syncSourceVersion,
            syncReceipt: syncReceipt?.record ?? null,
            candidates: noncePayload,
          }),
        )
      : null;

  return {
    candidates,
    removableRows,
    retainedProtectedRows,
    preservedUnknownRows,
    totalRemovable,
    totalRetainedProtected,
    totalPreservedUnknown,
    syncSourceVersion,
    confirmationNonce,
    blockers,
  };
}

export function previewSyntheticCleanup(
  workbook: WorkbookPort,
  sha256: Sha256,
): SyntheticCleanupPreview {
  const plan = buildPlan(workbook, sha256);
  const status =
    plan.blockers.length > 0
      ? "BLOCKED"
      : plan.totalRemovable === 0
        ? "NO_OP"
        : "PREVIEW";
  const safeResultCode =
    status === "BLOCKED"
      ? "CLEANUP_BLOCKED"
      : status === "NO_OP"
        ? "CLEANUP_NOOP"
        : "CLEANUP_PREVIEW_READY";
  return {
    status,
    schemaVersion: SHEETS_SCHEMA_VERSION,
    removableRows: plan.removableRows,
    retainedProtectedRows: plan.retainedProtectedRows,
    preservedUnknownRows: plan.preservedUnknownRows,
    totalRemovable: plan.totalRemovable,
    totalRetainedProtected: plan.totalRetainedProtected,
    totalPreservedUnknown: plan.totalPreservedUnknown,
    syncSourceVersion: plan.syncSourceVersion,
    confirmationNonce: plan.confirmationNonce,
    blockers: plan.blockers,
    safeResultCode,
  };
}

export function applySyntheticCleanup(
  workbook: WorkbookPort,
  confirmationNonce: string,
  sha256: Sha256,
): SyntheticCleanupApplyResult {
  const plan = buildPlan(workbook, sha256);
  if (plan.blockers.length > 0) throw new Error(plan.blockers[0]);
  if (plan.totalRemovable === 0) {
    return {
      status: "NO_OP",
      schemaVersion: SHEETS_SCHEMA_VERSION,
      deletedRows: emptyCounts(),
      totalDeleted: 0,
      retainedProtectedRows: plan.retainedProtectedRows,
      totalRetainedProtected: plan.totalRetainedProtected,
      preservedUnknownRows: plan.preservedUnknownRows,
      totalPreservedUnknown: plan.totalPreservedUnknown,
      safeResultCode: "CLEANUP_NOOP",
    };
  }
  if (!confirmationNonce || confirmationNonce !== plan.confirmationNonce)
    throw new Error("CLEANUP_CONFIRMATION_MISMATCH");

  const deletedRows = emptyCounts();
  for (const candidate of plan.candidates) {
    const sheet = workbook.getSheet(candidate.scope);
    const current = sheet?.getRowByPrimaryKey(
      candidate.primaryKey,
      candidate.value,
    );
    if (!current || canonicalJson(current) !== canonicalJson(candidate.record))
      throw new Error("CLEANUP_ROW_CHANGED");
    if (!sheet?.deleteRowByPrimaryKey(candidate.primaryKey, candidate.value))
      throw new Error("CLEANUP_ROW_CHANGED");
    deletedRows[candidate.scope] += 1;
  }
  return {
    status: "APPLIED",
    schemaVersion: SHEETS_SCHEMA_VERSION,
    deletedRows,
    totalDeleted: plan.totalRemovable,
    retainedProtectedRows: plan.retainedProtectedRows,
    totalRetainedProtected: plan.totalRetainedProtected,
    preservedUnknownRows: plan.preservedUnknownRows,
    totalPreservedUnknown: plan.totalPreservedUnknown,
    safeResultCode: "CLEANUP_APPLIED",
  };
}
