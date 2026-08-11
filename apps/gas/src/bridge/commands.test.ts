import { describe, expect, it } from "vitest";

import { bootstrapWorkbook } from "../sheets/bootstrap";
import { InMemoryWorkbook } from "../sheets/in-memory-workbook";
import { ackLabCommand, claimLabCommand, queueLabCommand } from "./commands";

const fakeSha = (value: string): string => value.length.toString(16).padStart(64, "0");

describe("Phase 2B command inbox", () => {
  it("offers fixed actions and metadata-only claims", () => {
    const workbook = new InMemoryWorkbook();
    bootstrapWorkbook(workbook, { dryRun: false });
    const row = queueLabCommand(
      workbook,
      "CREATE_BASIC",
      null,
      "2026-08-11T06:00:00Z",
    );
    expect(row.status).toBe("QUEUED");
    expect(JSON.stringify(row)).not.toMatch(/student|email|message|attachment/i);
    const claim = claimLabCommand(
      workbook,
      "local-worker",
      "SYNTHETIC-SHEET-FINGERPRINT",
      fakeSha,
      "2026-08-11T06:01:00Z",
      "2026-08-11T06:06:00Z",
      "token-a",
    );
    expect(claim?.envelope.commandId).toMatch(/^CMD-TST-/);
    expect(claim?.envelope.syntheticOnly).toBe(true);
    expect(ackLabCommand(workbook, claim!.envelope.commandId, "wrong", "APPLIED", "2026-08-11T06:02:00Z")).toBe(false);
    expect(ackLabCommand(workbook, claim!.envelope.commandId, "token-a", "APPLIED", "2026-08-11T06:02:00Z")).toBe(true);
  });

  it("reclaims an expired command and invalidates the stale token", () => {
    const workbook = new InMemoryWorkbook();
    bootstrapWorkbook(workbook, { dryRun: false });
    queueLabCommand(workbook, "CREATE_BASIC", null, "2026-08-11T06:00:00Z");
    const first = claimLabCommand(workbook, "a", "fp", fakeSha, "2026-08-11T06:00:01Z", "2026-08-11T06:00:02Z", "old");
    const second = claimLabCommand(workbook, "b", "fp", fakeSha, "2026-08-11T06:00:03Z", "2026-08-11T06:05:00Z", "new");
    expect(first).not.toBeNull();
    expect(second).not.toBeNull();
    expect(ackLabCommand(workbook, second!.envelope.commandId, "old", "APPLIED", "2026-08-11T06:00:04Z")).toBe(false);
    expect(ackLabCommand(workbook, second!.envelope.commandId, "new", "APPLIED", "2026-08-11T06:00:04Z")).toBe(true);
  });

  it("emits stale-version and bad-checksum fixtures without new command types", () => {
    const workbook = new InMemoryWorkbook();
    bootstrapWorkbook(workbook, { dryRun: false });
    queueLabCommand(workbook, "STALE_VERSION_TEST", null, "2026-08-11T06:00:00Z");
    const stale = claimLabCommand(workbook, "a", "fp", fakeSha, "2026-08-11T06:00:01Z", "2026-08-11T06:05:00Z", "a");
    expect(stale?.envelope.commandType).toBe("CREATE_SYNTHETIC_CASE");
    expect(stale?.envelope.sourceVersion).toBe(1);
    ackLabCommand(workbook, stale!.envelope.commandId, "a", "REJECTED", "2026-08-11T06:00:02Z");
    queueLabCommand(workbook, "BAD_CHECKSUM_TEST", null, "2026-08-11T06:01:00Z");
    const bad = claimLabCommand(workbook, "a", "fp", fakeSha, "2026-08-11T06:01:01Z", "2026-08-11T06:06:00Z", "b");
    expect(bad?.envelope.commandType).toBe("CREATE_SYNTHETIC_CASE");
    expect(bad?.envelope.checksum).toBe("0".repeat(64));
  });
});
