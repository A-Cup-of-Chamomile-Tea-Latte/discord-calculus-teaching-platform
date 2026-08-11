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
import { ackLabCommand, claimLabCommand } from "./bridge/commands";
import { GasWorkbookAdapter } from "./sheets/gas-workbook";

function stagingTarget(): { workbook: GasWorkbookAdapter; fingerprint: string } {
  const properties = PropertiesService.getScriptProperties();
  const spreadsheetId = properties.getProperty("PHASE2B_SPREADSHEET_ID");
  const fingerprint = properties.getProperty("PHASE2B_SPREADSHEET_FINGERPRINT");
  if (!spreadsheetId || !fingerprint) throw new Error("PHASE2B_TARGET_NOT_CONFIGURED");
  return {
    workbook: new GasWorkbookAdapter(SpreadsheetApp.openById(spreadsheetId)),
    fingerprint,
  };
}

export function standaloneBridgePreview(envelope: ProjectionEnvelope) {
  const target = stagingTarget();
  return previewProjection(target.workbook, envelope, target.fingerprint, gasSha256);
}

export function standaloneBridgeApply(
  envelope: ProjectionEnvelope,
  confirmationNonce: string,
) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("SYNC_LOCK_UNAVAILABLE");
  try {
    const target = stagingTarget();
    return applyProjection(
      target.workbook,
      envelope,
      confirmationNonce,
      target.fingerprint,
      gasSha256,
      new Date().toISOString(),
    );
  } finally {
    lock.releaseLock();
  }
}

export function standaloneBridgeClaimCommand(workerId: string) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("COMMAND_LOCK_UNAVAILABLE");
  try {
    const target = stagingTarget();
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

export function standaloneBridgeAckCommand(
  commandId: string,
  claimToken: string,
  resultCode: string,
) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10_000)) throw new Error("COMMAND_LOCK_UNAVAILABLE");
  try {
    const target = stagingTarget();
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
