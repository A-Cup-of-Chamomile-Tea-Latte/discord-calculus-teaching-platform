import { describe, expect, it } from "vitest";

import { bootstrapWorkbook } from "../sheets/bootstrap";
import { InMemoryWorkbook } from "../sheets/in-memory-workbook";
import {
  applyProjection,
  canonicalJson,
  checksumFor,
  previewProjection,
  type ProjectionEnvelope,
} from "./service";

const fingerprint = "SYNTHETIC-SHEET-FINGERPRINT";
const fakeSha = (value: string): string =>
  [...value]
    .reduce((sum, character) => sum + character.charCodeAt(0), 0)
    .toString(16)
    .padStart(64, "0");

function envelope(): ProjectionEnvelope {
  const value: ProjectionEnvelope = {
    schemaVersion: "2.0.0",
    environment: "STAGING",
    syntheticOnly: true,
    sourceVersion: 1,
    generatedAt: "2026-08-11T06:00:00Z",
    sourceFingerprint: fingerprint,
    scopes: ["Overview", "CaseBoard", "Operations", "History"],
    rowCounts: { Overview: 0, CaseBoard: 1, Operations: 0, History: 0 },
    rows: {
      Overview: [],
      CaseBoard: [
        {
          schemaVersion: "2.0.0",
          caseNumber: "TST-BASIC-001",
          moduleCode: "M01",
          status: "OPEN",
          assignedAlias: "SYN-LAB-TA",
          actionNeeded: "REVIEW",
          lastStudentAt: null,
          lastStaffAt: null,
          nextDeadlineAt: null,
          analysisEligible: false,
          updatedAt: "2026-08-11T06:00:00Z",
          sourceVersion: 1,
          sourceChecksum: "pending-v1",
        },
      ],
      Operations: [],
      History: [],
    },
    checksum: "",
  };
  value.checksum = checksumFor(
    value as unknown as Record<string, unknown>,
    fakeSha,
  );
  return value;
}

describe("Phase 2B GAS bridge", () => {
  it("canonicalizes recursively and rejects floating point values", () => {
    expect(canonicalJson({ b: { d: 2, c: 1 }, a: true })).toBe(
      '{"a":true,"b":{"c":1,"d":2}}',
    );
    expect(() => canonicalJson({ bad: 1.5 })).toThrow("FLOAT_NOT_ALLOWED");
  });

  it("previews without mutation and applies only with the same nonce", () => {
    const workbook = new InMemoryWorkbook();
    bootstrapWorkbook(workbook, { dryRun: false });
    const input = envelope();
    const before = JSON.stringify([...workbook.sheets.entries()]);
    const preview = previewProjection(workbook, input, fingerprint, fakeSha);
    expect(preview.status).toBe("PREVIEW");
    expect(JSON.stringify([...workbook.sheets.entries()])).toBe(before);
    expect(() =>
      applyProjection(
        workbook,
        input,
        "wrong",
        fingerprint,
        fakeSha,
        input.generatedAt,
      ),
    ).toThrow("CONFIRMATION_NONCE_MISMATCH");
    const applied = applyProjection(
      workbook,
      input,
      preview.confirmationNonce!,
      fingerprint,
      fakeSha,
      input.generatedAt,
    );
    expect(applied.status).toBe("APPLIED");
    expect(workbook.getSheet("CaseBoard")?.rows).toHaveLength(1);
    expect(workbook.getSheet("_SyncState")?.rows).toContainEqual(
      expect.objectContaining({
        syncKey: "phase2b.local-projection",
        status: "SUCCESS",
      }),
    );
  });

  it("treats identical delivery as no-op and rejects conflicts", () => {
    const workbook = new InMemoryWorkbook();
    bootstrapWorkbook(workbook, { dryRun: false });
    const input = envelope();
    const preview = previewProjection(workbook, input, fingerprint, fakeSha);
    applyProjection(
      workbook,
      input,
      preview.confirmationNonce!,
      fingerprint,
      fakeSha,
      input.generatedAt,
    );
    expect(
      previewProjection(workbook, input, fingerprint, fakeSha).status,
    ).toBe("NO_OP");
    const conflict = { ...input, checksum: "f".repeat(64) };
    expect(() =>
      previewProjection(workbook, conflict, fingerprint, fakeSha),
    ).toThrow("SYNC_BAD_CHECKSUM");
    expect(() =>
      previewProjection(
        workbook,
        { ...input, sourceFingerprint: "wrong" },
        fingerprint,
        fakeSha,
      ),
    ).toThrow("SYNC_WRONG_TARGET");
  });
});
