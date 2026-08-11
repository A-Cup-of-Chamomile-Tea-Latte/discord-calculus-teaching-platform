import type { SheetRecord, WorkbookPort } from "../sheets/bootstrap";

export interface ProjectionEnvelope {
  schemaVersion: string;
  environment: string;
  syntheticOnly: boolean;
  sourceVersion: number;
  generatedAt: string;
  sourceFingerprint: string;
  scopes: string[];
  rowCounts: Record<string, number>;
  rows: Record<string, SheetRecord[]>;
  checksum: string;
}

export interface BridgeReceipt {
  status: "PREVIEW" | "APPLIED" | "NO_OP";
  sourceVersion: number;
  checksum: string;
  confirmationNonce?: string;
  rowCounts: Record<string, number>;
  safeResultCode: string;
}

export type Sha256 = (value: string) => string;

const ALLOWED_SCOPES = ["Overview", "CaseBoard", "Operations", "History"];
const PRIMARY_KEYS: Record<string, string> = {
  Overview: "metricKey",
  CaseBoard: "caseNumber",
  Operations: "operationKey",
  History: "eventRef",
};

function sorted(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sorted);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, sorted(item)]),
    );
  }
  if (typeof value === "number" && !Number.isInteger(value))
    throw new Error("FLOAT_NOT_ALLOWED");
  return value;
}

export function canonicalJson(
  value: Record<string, unknown>,
  excludeChecksum = false,
): string {
  const copy = { ...value };
  if (excludeChecksum) delete copy.checksum;
  return JSON.stringify(sorted(copy));
}

export function gasSha256(value: string): string {
  return Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    value,
    Utilities.Charset.UTF_8,
  )
    .map((byte) => (byte < 0 ? byte + 256 : byte).toString(16).padStart(2, "0"))
    .join("");
}

export function checksumFor(
  envelope: Record<string, unknown>,
  sha256: Sha256,
): string {
  return sha256(canonicalJson(envelope, true));
}

function syncRecord(workbook: WorkbookPort): SheetRecord | null {
  return workbook
    .getSheet("_SyncState")
    ?.getRowByPrimaryKey("syncKey", "phase2b.local-projection") ?? null;
}

function validate(
  workbook: WorkbookPort,
  envelope: ProjectionEnvelope,
  fingerprint: string,
  sha256: Sha256,
): "NEW" | "NO_OP" {
  if (envelope.sourceFingerprint !== fingerprint)
    throw new Error("SYNC_WRONG_TARGET");
  if (envelope.schemaVersion !== "2.0.0")
    throw new Error("SYNC_SCHEMA_VERSION_UNSUPPORTED");
  if (envelope.environment !== "STAGING")
    throw new Error("SYNC_WRONG_ENVIRONMENT");
  if (envelope.syntheticOnly !== true)
    throw new Error("SYNC_NON_SYNTHETIC_REFUSED");
  if (checksumFor(envelope as unknown as Record<string, unknown>, sha256) !== envelope.checksum)
    throw new Error("SYNC_BAD_CHECKSUM");
  if (
    envelope.scopes.length !== ALLOWED_SCOPES.length ||
    envelope.scopes.some((scope, index) => scope !== ALLOWED_SCOPES[index])
  )
    throw new Error("SYNC_SCOPE_REFUSED");
  const current = syncRecord(workbook);
  if (!current) return "NEW";
  const version = Number(current.sourceVersion ?? 0);
  const checksum = String(current.sourceChecksum ?? "");
  if (envelope.sourceVersion < version) throw new Error("SYNC_STALE_VERSION");
  if (envelope.sourceVersion === version && envelope.checksum !== checksum)
    throw new Error("SYNC_VERSION_CHECKSUM_CONFLICT");
  return envelope.sourceVersion === version ? "NO_OP" : "NEW";
}

export function previewProjection(
  workbook: WorkbookPort,
  envelope: ProjectionEnvelope,
  fingerprint: string,
  sha256: Sha256,
): BridgeReceipt {
  const state = validate(workbook, envelope, fingerprint, sha256);
  return {
    status: state === "NO_OP" ? "NO_OP" : "PREVIEW",
    sourceVersion: envelope.sourceVersion,
    checksum: envelope.checksum,
    confirmationNonce: sha256(`${canonicalJson(envelope as unknown as Record<string, unknown>)}\nPHASE2B_APPLY`).slice(0, 24),
    rowCounts: { ...envelope.rowCounts },
    safeResultCode: state === "NO_OP" ? "SYNC_NOOP" : "SYNC_PREVIEW_READY",
  };
}

export function applyProjection(
  workbook: WorkbookPort,
  envelope: ProjectionEnvelope,
  confirmationNonce: string,
  fingerprint: string,
  sha256: Sha256,
  now: string,
): BridgeReceipt {
  const preview = previewProjection(workbook, envelope, fingerprint, sha256);
  if (confirmationNonce !== preview.confirmationNonce)
    throw new Error("CONFIRMATION_NONCE_MISMATCH");
  if (preview.status === "NO_OP") return preview;
  for (const scope of ALLOWED_SCOPES) {
    const sheet = workbook.getSheet(scope);
    if (!sheet) throw new Error(`SYNC_SHEET_MISSING_${scope.toUpperCase()}`);
    const primaryKey = PRIMARY_KEYS[scope];
    for (const row of envelope.rows[scope] ?? []) {
      const key = String(row[primaryKey] ?? "");
      if (!key) throw new Error("SYNC_PRIMARY_KEY_REQUIRED");
      sheet.upsertRowByPrimaryKey(primaryKey, key, row);
    }
  }
  const sync = workbook.getSheet("_SyncState");
  if (!sync) throw new Error("SYNC_STATE_SHEET_MISSING");
  sync.upsertRowByPrimaryKey("syncKey", "phase2b.local-projection", {
    schemaVersion: "2.0.0",
    syncKey: "phase2b.local-projection",
    direction: "LOCAL_TO_CLOUD",
    sourceName: "staging.sqlite3",
    sourceVersion: envelope.sourceVersion,
    sourceChecksum: envelope.checksum,
    cursorRef: null,
    status: "SUCCESS",
    lastAttemptAt: now,
    lastSuccessAt: now,
    safeErrorCode: null,
    operatorConfirmedAt: now,
    updatedAt: now,
  });
  return { ...preview, status: "APPLIED", safeResultCode: "SYNC_APPLIED" };
}
