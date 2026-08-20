import { describe, expect, it } from "vitest";

import { bootstrapWorkbook } from "./bootstrap";
import { InMemoryWorkbook } from "./in-memory-workbook";
import {
  applySyntheticCleanup,
  previewSyntheticCleanup,
} from "./synthetic-cleanup";

const fakeSha = (value: string): string =>
  [...value]
    .reduce((sum, character) => sum + character.charCodeAt(0), 0)
    .toString(16)
    .padStart(64, "0");

function seededWorkbook(): InMemoryWorkbook {
  const workbook = new InMemoryWorkbook();
  bootstrapWorkbook(workbook, { dryRun: false });
  workbook.getSheet("Overview")?.appendFixtureRow({
    metricKey: "cases.open",
    metricValue: "1",
    status: "STAGING",
    description: "Synthetic count",
    sourceReceipt: "STAGING-SQLITE",
  });
  workbook.getSheet("Overview")?.appendFixtureRow({
    metricKey: "operator.note",
    status: "MANUAL",
    description: "Preserve me",
  });
  workbook.getSheet("CaseBoard")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    caseNumber: "TST-CLEANUP-001",
    assignedAlias: "SYN-LAB-TA",
    analysisEligible: false,
  });
  workbook.getSheet("Operations")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    operationKey: "data-bridge",
    service: "calculus-data-bridge",
    component: "projection-outbox",
    mode: "SYNTHETIC_ONLY",
  });
  workbook.getSheet("History")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    eventRef: "synthetic-event-ref",
    subjectRef: "TST-CLEANUP-001",
    summaryCode: "SYNTHETIC_CASE_OPEN",
    source: "LOCAL_FIXTURE",
  });
  workbook.getSheet("History")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    eventRef: "synthetic-command-event-ref",
    subjectRef: "TST-CLEANUP-001",
    summaryCode: "SYNTHETIC_CASE_REOPEN",
    source: "CLOUD_COMMAND",
  });
  workbook.getSheet("_CommandInbox")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    jobRef: "CMD-TST-CLEANUP-001",
    payloadRef: "fixture://case/basic",
    idempotencyKey: "phase2b:cleanup",
    status: "COMPLETED",
  });
  workbook.getSheet("_SyncState")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    syncKey: "phase2b.local-projection",
    direction: "LOCAL_TO_CLOUD",
    sourceName: "staging.sqlite3",
    sourceVersion: 7,
    sourceChecksum: "a".repeat(64),
    status: "SUCCESS",
  });
  workbook.getSheet("_EmailOutbox")?.appendFixtureRow({
    jobRef: "operator-email-row",
  });
  workbook.getSheet("Members")?.appendFixtureRow({ memberRef: "preserved" });
  return workbook;
}

describe("synthetic Sheet cleanup", () => {
  it("previews, deletes only strict synthetic rows, and becomes a no-op", () => {
    const workbook = seededWorkbook();
    const before = JSON.stringify([...workbook.sheets.entries()]);
    const preview = previewSyntheticCleanup(workbook, fakeSha);

    expect(preview.status).toBe("PREVIEW");
    expect(preview.totalRemovable).toBe(5);
    expect(preview.totalRetainedProtected).toBe(1);
    expect(preview.totalPreservedUnknown).toBe(2);
    expect(JSON.stringify([...workbook.sheets.entries()])).toBe(before);

    const applied = applySyntheticCleanup(
      workbook,
      preview.confirmationNonce!,
      fakeSha,
    );
    expect(applied.status).toBe("APPLIED");
    expect(applied.totalDeleted).toBe(5);
    expect(workbook.getSheet("Overview")?.rows).toEqual([
      expect.objectContaining({ metricKey: "operator.note" }),
    ]);
    expect(workbook.getSheet("_EmailOutbox")?.rows).toHaveLength(1);
    expect(workbook.getSheet("_CommandInbox")?.rows).toHaveLength(1);
    expect(workbook.getSheet("_SyncState")?.rows).toHaveLength(1);
    expect(workbook.getSheet("Members")?.rows).toHaveLength(1);
    expect(workbook.getSheet("_Settings")?.rows.length).toBeGreaterThan(0);
    expect(previewSyntheticCleanup(workbook, fakeSha).status).toBe("NO_OP");
  });

  it("rejects a changed plan between preview and apply", () => {
    const workbook = seededWorkbook();
    const preview = previewSyntheticCleanup(workbook, fakeSha);
    workbook.getSheet("CaseBoard")?.appendFixtureRow({
      schemaVersion: "2.0.0",
      caseNumber: "TST-CLEANUP-002",
      assignedAlias: "SYN-LAB-TA",
      analysisEligible: false,
    });
    expect(() =>
      applySyntheticCleanup(workbook, preview.confirmationNonce!, fakeSha),
    ).toThrow("CLEANUP_CONFIRMATION_MISMATCH");
  });

  it("fails closed when synthetic rows have no sync receipt", () => {
    const workbook = seededWorkbook();
    workbook
      .getSheet("_SyncState")
      ?.deleteRowByPrimaryKey("syncKey", "phase2b.local-projection");
    const preview = previewSyntheticCleanup(workbook, fakeSha);
    expect(preview.status).toBe("BLOCKED");
    expect(preview.blockers).toEqual(["SYNTHETIC_SYNC_RECEIPT_REQUIRED"]);
    expect(() => applySyntheticCleanup(workbook, "anything", fakeSha)).toThrow(
      "SYNTHETIC_SYNC_RECEIPT_REQUIRED",
    );
  });

  it("blocks duplicate primary keys instead of deleting either row", () => {
    const workbook = seededWorkbook();
    workbook.getSheet("CaseBoard")?.appendFixtureRow({
      schemaVersion: "2.0.0",
      caseNumber: "TST-CLEANUP-001",
      assignedAlias: "operator-row",
      analysisEligible: true,
    });
    const preview = previewSyntheticCleanup(workbook, fakeSha);
    expect(preview.status).toBe("BLOCKED");
    expect(preview.blockers).toContain(
      "CLEANUP_DUPLICATE_PRIMARY_KEY_CaseBoard",
    );
    expect(workbook.getSheet("CaseBoard")?.rows).toHaveLength(2);
  });

  it("can resume safely after a partial deletion failure", () => {
    const workbook = seededWorkbook();
    const preview = previewSyntheticCleanup(workbook, fakeSha);
    const history = workbook.getSheet("History");
    if (!history) throw new Error("test setup failed");
    const originalDelete = history.deleteRowByPrimaryKey.bind(history);
    let failOnce = true;
    history.deleteRowByPrimaryKey = (...arguments_) => {
      if (failOnce) {
        failOnce = false;
        return false;
      }
      return originalDelete(...arguments_);
    };
    expect(() =>
      applySyntheticCleanup(workbook, preview.confirmationNonce!, fakeSha),
    ).toThrow("CLEANUP_ROW_CHANGED");

    const retryPreview = previewSyntheticCleanup(workbook, fakeSha);
    expect(retryPreview.status).toBe("PREVIEW");
    expect(retryPreview.totalRemovable).toBe(2);
    expect(
      applySyntheticCleanup(workbook, retryPreview.confirmationNonce!, fakeSha)
        .status,
    ).toBe("APPLIED");
    expect(previewSyntheticCleanup(workbook, fakeSha).status).toBe("NO_OP");
  });
});
