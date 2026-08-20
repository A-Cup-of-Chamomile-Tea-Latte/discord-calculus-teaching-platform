export { bootstrapSheetsApply, bootstrapSheetsDryRun } from "./index";

import {
  applyProjection,
  gasSha256,
  previewProjection,
  type ProjectionEnvelope,
} from "./bridge/service";
import {
  ackLabCommand,
  claimLabCommand,
  peekLabCommands,
} from "./bridge/commands";
import { GasWorkbookAdapter } from "./sheets/gas-workbook";
import { SHEET_SCHEMAS } from "./sheets/schema";
import {
  applySyntheticCleanup,
  previewSyntheticCleanup,
} from "./sheets/synthetic-cleanup";

interface BridgeTarget {
  workbook: GasWorkbookAdapter;
  fingerprint: string;
  environment: "STAGING" | "PRODUCTION";
  syntheticOnly: boolean;
}

const REQUIRED_BRIDGE_SHEETS = SHEET_SCHEMAS.map((sheet) => sheet.name);

export function bridgeConfigureTarget(
  spreadsheetId: string,
  fingerprint: string,
  environment: string,
  syntheticOnly: boolean,
) {
  const normalizedId = String(spreadsheetId ?? "").trim();
  const normalizedFingerprint = String(fingerprint ?? "")
    .trim()
    .toLowerCase();
  const normalizedEnvironment = String(environment ?? "")
    .trim()
    .toUpperCase();
  if (!/^[A-Za-z0-9_-]{20,}$/.test(normalizedId))
    throw new Error("BRIDGE_SPREADSHEET_ID_INVALID");
  if (!/^[a-f0-9]{64}$/.test(normalizedFingerprint))
    throw new Error("BRIDGE_FINGERPRINT_INVALID");
  if (
    normalizedEnvironment !== "STAGING" &&
    normalizedEnvironment !== "PRODUCTION"
  )
    throw new Error("BRIDGE_ENVIRONMENT_INVALID");
  if ((normalizedEnvironment === "STAGING") !== Boolean(syntheticOnly))
    throw new Error("BRIDGE_MODE_MISMATCH");

  const spreadsheet = SpreadsheetApp.openById(normalizedId);
  const present = new Set(
    spreadsheet.getSheets().map((sheet) => sheet.getName()),
  );
  const missing = REQUIRED_BRIDGE_SHEETS.filter((name) => !present.has(name));
  if (missing.length > 0) throw new Error("BRIDGE_SCHEMA_INCOMPLETE");

  const properties = PropertiesService.getScriptProperties();
  properties
    .setProperty("BRIDGE_SPREADSHEET_ID", normalizedId)
    .setProperty("BRIDGE_SPREADSHEET_FINGERPRINT", normalizedFingerprint)
    .setProperty("BRIDGE_ENVIRONMENT", normalizedEnvironment)
    .setProperty("BRIDGE_SYNTHETIC_ONLY", String(Boolean(syntheticOnly)))
    .deleteProperty("PHASE2B_SPREADSHEET_ID")
    .deleteProperty("PHASE2B_SPREADSHEET_FINGERPRINT");
  return {
    ok: true,
    configured: true,
    environment: normalizedEnvironment,
    syntheticOnly: Boolean(syntheticOnly),
    schemaVersion: "2.0.0",
  };
}

function bridgeTarget(): BridgeTarget {
  const properties = PropertiesService.getScriptProperties();
  const spreadsheetId =
    properties.getProperty("BRIDGE_SPREADSHEET_ID") ??
    properties.getProperty("PHASE2B_SPREADSHEET_ID");
  const fingerprint =
    properties.getProperty("BRIDGE_SPREADSHEET_FINGERPRINT") ??
    properties.getProperty("PHASE2B_SPREADSHEET_FINGERPRINT");
  const environment = properties.getProperty("BRIDGE_ENVIRONMENT") ?? "STAGING";
  const syntheticOnly =
    (properties.getProperty("BRIDGE_SYNTHETIC_ONLY") ?? "true") === "true";
  if (!spreadsheetId || !fingerprint)
    throw new Error("BRIDGE_TARGET_NOT_CONFIGURED");
  if (environment !== "STAGING" && environment !== "PRODUCTION")
    throw new Error("BRIDGE_ENVIRONMENT_INVALID");
  if ((environment === "STAGING") !== syntheticOnly)
    throw new Error("BRIDGE_MODE_MISMATCH");
  return {
    workbook: new GasWorkbookAdapter(SpreadsheetApp.openById(spreadsheetId)),
    fingerprint,
    environment,
    syntheticOnly,
  };
}

export function bridgeHealth() {
  const target = bridgeTarget();
  return {
    ok: true,
    service: "calculus-gas-bridge",
    environment: target.environment,
    syntheticOnly: target.syntheticOnly,
    schemaVersion: "2.0.0",
  };
}

export function bridgePreview(envelope: ProjectionEnvelope) {
  const target = bridgeTarget();
  return previewProjection(
    target.workbook,
    envelope,
    target.fingerprint,
    gasSha256,
    target.environment,
    target.syntheticOnly,
  );
}

export function bridgeApply(
  envelope: ProjectionEnvelope,
  confirmationNonce: string,
) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("SYNC_LOCK_UNAVAILABLE");
  try {
    const target = bridgeTarget();
    return applyProjection(
      target.workbook,
      envelope,
      confirmationNonce,
      target.fingerprint,
      gasSha256,
      new Date().toISOString(),
      target.environment,
      target.syntheticOnly,
    );
  } finally {
    lock.releaseLock();
  }
}

function assertSyntheticCleanupTarget(target: BridgeTarget): void {
  if (target.environment !== "STAGING" || !target.syntheticOnly)
    throw new Error("CLEANUP_REQUIRES_SYNTHETIC_STAGING");
}

export function bridgeSyntheticCleanupDryRun() {
  const target = bridgeTarget();
  assertSyntheticCleanupTarget(target);
  return previewSyntheticCleanup(target.workbook, gasSha256);
}

export function bridgeSyntheticCleanupApply(confirmationNonce: string) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("CLEANUP_LOCK_UNAVAILABLE");
  try {
    const target = bridgeTarget();
    assertSyntheticCleanupTarget(target);
    return applySyntheticCleanup(
      target.workbook,
      String(confirmationNonce ?? ""),
      gasSha256,
    );
  } finally {
    lock.releaseLock();
  }
}

export function bridgePeekCommands(limit: number) {
  const target = bridgeTarget();
  if (!target.syntheticOnly) return [];
  return peekLabCommands(target.workbook, limit, target.fingerprint, gasSha256);
}

export function bridgeClaimCommand(workerId: string) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("COMMAND_LOCK_UNAVAILABLE");
  try {
    const target = bridgeTarget();
    if (!target.syntheticOnly) return null;
    const now = new Date();
    const lease = new Date(now.getTime() + 5 * 60 * 1000);
    const token = gasSha256(`${workerId}\n${now.toISOString()}`).slice(0, 32);
    return claimLabCommand(
      target.workbook,
      workerId,
      target.fingerprint,
      gasSha256,
      now.toISOString(),
      lease.toISOString(),
      token,
    );
  } finally {
    lock.releaseLock();
  }
}

export function bridgeAckCommand(
  commandId: string,
  claimToken: string,
  resultCode: string,
) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("COMMAND_LOCK_UNAVAILABLE");
  try {
    const target = bridgeTarget();
    if (!target.syntheticOnly) return false;
    return ackLabCommand(
      target.workbook,
      commandId,
      claimToken,
      resultCode,
      new Date().toISOString(),
    );
  } finally {
    lock.releaseLock();
  }
}
