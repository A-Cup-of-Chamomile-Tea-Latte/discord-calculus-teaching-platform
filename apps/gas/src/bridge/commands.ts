import type { SheetRecord, WorkbookPort } from "../sheets/bootstrap";
import { canonicalJson, type Sha256 } from "./service";

export type LabAction =
  | "CREATE_BASIC"
  | "CLOSE_CASE"
  | "REOPEN_CASE"
  | "REPLAY_LAST"
  | "STALE_VERSION_TEST"
  | "BAD_CHECKSUM_TEST";

export interface CommandEnvelope {
  schemaVersion: string;
  environment: string;
  syntheticOnly: true;
  commandId: string;
  commandType: string;
  payloadRef: string;
  targetCaseRef: string | null;
  idempotencyKey: string;
  sourceVersion: number;
  requestedAt: string;
  sourceFingerprint: string;
  checksum: string;
}

export interface CommandClaim {
  envelope: CommandEnvelope;
  claimToken: string;
  leaseExpiresAt: string;
}

const ACTIONS: Record<
  LabAction,
  { commandType: string; payloadRef: string; targetRequired: boolean }
> = {
  CREATE_BASIC: {
    commandType: "CREATE_SYNTHETIC_CASE",
    payloadRef: "fixture://public/basic-v1",
    targetRequired: false,
  },
  CLOSE_CASE: {
    commandType: "CLOSE_SYNTHETIC_CASE",
    payloadRef: "fixture://public/close-reopen-v1",
    targetRequired: true,
  },
  REOPEN_CASE: {
    commandType: "REOPEN_SYNTHETIC_CASE",
    payloadRef: "fixture://public/close-reopen-v1",
    targetRequired: true,
  },
  REPLAY_LAST: {
    commandType: "REPLAY_LAST_SYNTHETIC_COMMAND",
    payloadRef: "fixture://public/basic-v1",
    targetRequired: false,
  },
  STALE_VERSION_TEST: {
    commandType: "CREATE_SYNTHETIC_CASE",
    payloadRef: "fixture://failure/stale-version-v1",
    targetRequired: false,
  },
  BAD_CHECKSUM_TEST: {
    commandType: "CREATE_SYNTHETIC_CASE",
    payloadRef: "fixture://failure/bad-checksum-v1",
    targetRequired: false,
  },
};

function commandRows(workbook: WorkbookPort): SheetRecord[] {
  const sheet = workbook.getSheet("_CommandInbox");
  if (!sheet) throw new Error("COMMAND_INBOX_MISSING");
  return sheet
    .getColumnValues("jobRef")
    .filter(Boolean)
    .map((jobRef) => sheet.getRowByPrimaryKey("jobRef", jobRef))
    .filter((row): row is SheetRecord => row !== null);
}

function nextVersion(workbook: WorkbookPort): number {
  const rows = commandRows(workbook);
  return rows.reduce((maximum, row) => {
    const match = /^CMD-TST-v(\d+)-/.exec(String(row.jobRef ?? ""));
    return Math.max(maximum, match ? Number(match[1]) : 0);
  }, 0) + 1;
}

export function queueLabCommand(
  workbook: WorkbookPort,
  action: LabAction,
  targetCaseRef: string | null,
  now: string,
): SheetRecord {
  const definition = ACTIONS[action];
  if (!definition) throw new Error("COMMAND_ACTION_UNSUPPORTED");
  if (definition.targetRequired && !targetCaseRef?.startsWith("TST-"))
    throw new Error("TARGET_CASE_REF_REQUIRED");
  if (targetCaseRef !== null && !targetCaseRef.startsWith("TST-"))
    throw new Error("TARGET_CASE_REF_INVALID");
  const regularVersion = nextVersion(workbook);
  const version = action === "STALE_VERSION_TEST" ? 1 : regularVersion;
  const suffix = now.replace(/\D/g, "").slice(-14);
  const jobRef = `CMD-TST-v${version}-${suffix}-${action}`;
  const row: SheetRecord = {
    schemaVersion: "2.0.0",
    jobRef,
    commandType: definition.commandType,
    payloadRef: definition.payloadRef,
    targetRef: targetCaseRef,
    status: "QUEUED",
    idempotencyKey: `phase2b:${jobRef}`,
    claimedBy: null,
    leaseExpiresAt: null,
    attemptCount: 0,
    retryAt: null,
    safeErrorCode: null,
    createdAt: now,
    updatedAt: now,
  };
  const sheet = workbook.getSheet("_CommandInbox");
  if (!sheet) throw new Error("COMMAND_INBOX_MISSING");
  sheet.upsertRowByPrimaryKey("jobRef", jobRef, row);
  return row;
}

function buildEnvelope(
  row: SheetRecord,
  fingerprint: string,
  sha256: Sha256,
): CommandEnvelope {
  const match = /^CMD-TST-v(\d+)-/.exec(String(row.jobRef ?? ""));
  if (!match) throw new Error("COMMAND_VERSION_MISSING");
  const envelope: CommandEnvelope = {
    schemaVersion: "2.0.0",
    environment: "STAGING",
    syntheticOnly: true,
    commandId: String(row.jobRef),
    commandType: String(row.commandType),
    payloadRef: String(row.payloadRef),
    targetCaseRef: row.targetRef ? String(row.targetRef) : null,
    idempotencyKey: String(row.idempotencyKey),
    sourceVersion: Number(match[1]),
    requestedAt: String(row.createdAt),
    sourceFingerprint: fingerprint,
    checksum: "",
  };
  envelope.checksum = sha256(
    canonicalJson(envelope as unknown as Record<string, unknown>, true),
  );
  if (envelope.payloadRef === "fixture://failure/bad-checksum-v1")
    envelope.checksum = "0".repeat(64);
  return envelope;
}

export function claimLabCommand(
  workbook: WorkbookPort,
  workerId: string,
  fingerprint: string,
  sha256: Sha256,
  now: string,
  leaseExpiresAt: string,
  claimToken: string,
): CommandClaim | null {
  const sheet = workbook.getSheet("_CommandInbox");
  if (!sheet) throw new Error("COMMAND_INBOX_MISSING");
  const candidate = commandRows(workbook).find((row) => {
    const expired =
      row.status === "CLAIMED" &&
      row.leaseExpiresAt !== null &&
      String(row.leaseExpiresAt) <= now;
    return row.status === "QUEUED" || expired;
  });
  if (!candidate) return null;
  const jobRef = String(candidate.jobRef);
  const updated: SheetRecord = {
    ...candidate,
    status: "CLAIMED",
    claimedBy: `${workerId}#${claimToken}`,
    leaseExpiresAt,
    attemptCount: Number(candidate.attemptCount ?? 0) + 1,
    safeErrorCode: null,
    updatedAt: now,
  };
  sheet.upsertRowByPrimaryKey("jobRef", jobRef, updated);
  const envelope = buildEnvelope(
    updated,
    fingerprint,
    sha256,
  );
  return { envelope, claimToken, leaseExpiresAt };
}

export function ackLabCommand(
  workbook: WorkbookPort,
  commandId: string,
  claimToken: string,
  resultCode: string,
  now: string,
): boolean {
  const sheet = workbook.getSheet("_CommandInbox");
  if (!sheet) throw new Error("COMMAND_INBOX_MISSING");
  const row = sheet.getRowByPrimaryKey("jobRef", commandId);
  if (
    !row ||
    row.status !== "CLAIMED" ||
    !String(row.claimedBy).endsWith(`#${claimToken}`)
  )
    return false;
  sheet.upsertRowByPrimaryKey("jobRef", commandId, {
    ...row,
    status: resultCode === "REJECTED" ? "REJECTED" : "COMPLETED",
    claimedBy: null,
    leaseExpiresAt: null,
    safeErrorCode: resultCode,
    updatedAt: now,
  });
  return true;
}
