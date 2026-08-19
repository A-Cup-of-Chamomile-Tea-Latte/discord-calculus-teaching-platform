export {
  bootstrapSheetsApply,
  bootstrapSheetsDryRun,
  doGet,
  doPost,
} from "./index";

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

interface BridgeTarget {
  workbook: GasWorkbookAdapter;
  fingerprint: string;
  environment: "STAGING" | "PRODUCTION";
  syntheticOnly: boolean;
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
  if (!spreadsheetId || !fingerprint) throw new Error("BRIDGE_TARGET_NOT_CONFIGURED");
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

// Transitional aliases are kept only so an older immutable staging deployment
// can be compared during cutover. New deployments expose the concise names.
export const standaloneBridgePreview = bridgePreview;
export const standaloneBridgeApply = bridgeApply;
export const standaloneBridgeClaimCommand = bridgeClaimCommand;
export const standaloneBridgeAckCommand = bridgeAckCommand;
