import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { bootstrapWorkbook, migrateToCompactWorkbook } from "./bootstrap";
import type { InMemorySheetSeed } from "./in-memory-workbook";
import { InMemoryWorkbook } from "./in-memory-workbook";
import {
  headersFor,
  HUMAN_VIEW_SHEETS,
  LEGACY_FULL_SCHEMA_SHEETS,
  MACHINE_VIEW_SHEETS,
  SCHEMA_METADATA_ROWS,
  SHEET_SCHEMAS,
  SHEETS_SCHEMA_VERSION,
} from "./schema";

const expectedSheets = [...HUMAN_VIEW_SHEETS, ...MACHINE_VIEW_SHEETS];

function legacySeed(): Record<string, InMemorySheetSeed> {
  return Object.fromEntries(
    LEGACY_FULL_SCHEMA_SHEETS.map((name) => [
      name,
      name === "Settings"
        ? {
            headers: ["settingKey", "settingValue", "description", "updatedAt"],
            rows: [
              {
                settingKey: "schema.version",
                settingValue: "1.3.0",
              },
              {
                settingKey: "schema.migration.last",
                settingValue: "0004-command-email-queues",
              },
            ],
          }
        : { headers: ["legacyHeader"], rows: [] },
    ]),
  );
}

describe("compact Sheets schema", () => {
  it("defines five human views and five machine views", () => {
    expect(SHEET_SCHEMAS.map((sheet) => sheet.name)).toEqual(expectedSheets);
    expect(
      SHEET_SCHEMAS.filter((sheet) => sheet.audience === "HUMAN").map(
        (sheet) => sheet.name,
      ),
    ).toEqual(HUMAN_VIEW_SHEETS);
    expect(
      SHEET_SCHEMAS.filter((sheet) => sheet.audience === "MACHINE").map(
        (sheet) => sheet.name,
      ),
    ).toEqual(MACHINE_VIEW_SHEETS);
    for (const sheet of SHEET_SCHEMAS) {
      const headers = headersFor(sheet);
      expect(new Set(headers).size).toBe(headers.length);
      expect(headers).toContain(sheet.primaryKey);
      expect(sheet.indexes.length).toBeGreaterThan(0);
      expect(sheet.retention.length).toBeGreaterThan(20);
      expect(sheet.sourceContracts.length).toBeGreaterThan(0);
    }
  });

  it("keeps Members useful without names, student IDs or email addresses", () => {
    const members = SHEET_SCHEMAS.find((sheet) => sheet.name === "Members");
    expect(members).toBeDefined();
    const headers = headersFor(members!);
    expect(headers).toContain("membershipStatus");
    expect(headers).toContain("verificationStatus");
    expect(headers).toContain("analysisDefault");
    expect(headers).not.toContain("name");
    expect(headers).not.toContain("studentId");
    expect(headers).not.toContain("email");
    expect(headers).not.toContain("discordUserId");
  });

  it("provides cloud-visible bot health without process details or logs", () => {
    const operations = SHEET_SCHEMAS.find(
      (sheet) => sheet.name === "Operations",
    );
    expect(operations).toBeDefined();
    const headers = headersFor(operations!);
    expect(headers).toContain("service");
    expect(headers).toContain("status");
    expect(headers).toContain("lastHeartbeatAt");
    expect(headers).toContain("queueDepth");
    expect(headers).toContain("safeErrorCode");
    expect(headers).not.toContain("pid");
    expect(headers).not.toContain("logBody");
  });

  it("keeps both queues metadata-only, claimable and idempotent", () => {
    const commands = SHEET_SCHEMAS.find(
      (sheet) => sheet.name === "_CommandInbox",
    );
    const email = SHEET_SCHEMAS.find((sheet) => sheet.name === "_EmailOutbox");
    expect(commands).toBeDefined();
    expect(email).toBeDefined();

    const commandHeaders = headersFor(commands!);
    expect(commandHeaders).toContain("payloadRef");
    expect(commandHeaders).toContain("idempotencyKey");
    expect(commandHeaders).toContain("leaseExpiresAt");
    expect(commandHeaders).not.toContain("payloadJson");
    expect(commandHeaders).not.toContain("botToken");

    const emailHeaders = headersFor(email!);
    expect(emailHeaders).toContain("recipientRef");
    expect(emailHeaders).toContain("providerAcceptedAt");
    expect(emailHeaders).not.toContain("recipientEmail");
    expect(emailHeaders).not.toContain("subject");
    expect(emailHeaders).not.toContain("body");
    expect(emailHeaders).not.toContain("verificationCode");
  });

  it("keeps every fixture seed key within its sheet contract", () => {
    const seed = JSON.parse(
      readFileSync(
        new URL("../../fixtures/sheets-seed.json", import.meta.url),
        "utf8",
      ),
    ) as { sheets: Record<string, Array<Record<string, unknown>>> };
    expect(Object.keys(seed.sheets)).toEqual(expectedSheets);
    for (const definition of SHEET_SCHEMAS) {
      const allowed = new Set(headersFor(definition));
      for (const row of seed.sheets[definition.name] ?? []) {
        expect(Object.keys(row).every((key) => allowed.has(key))).toBe(true);
      }
    }
  });

  it("bootstraps the compact schema and is idempotent", () => {
    const workbook = new InMemoryWorkbook();
    const dryRun = bootstrapWorkbook(workbook, { dryRun: true });
    expect(dryRun.changed).toBe(true);
    expect(
      dryRun.actions.filter((action) => action.type === "CREATE_SHEET"),
    ).toHaveLength(expectedSheets.length);
    expect(workbook.sheets.size).toBe(0);

    const first = bootstrapWorkbook(workbook, { dryRun: false });
    expect(first.changed).toBe(true);
    expect([...workbook.sheets.keys()]).toEqual(expectedSheets);
    const settings = workbook.getSheet("_Settings");
    expect(settings?.rows).toHaveLength(SCHEMA_METADATA_ROWS.length);
    expect(settings?.rows[0]).toMatchObject({
      settingKey: "schema.version",
      settingValue: SHEETS_SCHEMA_VERSION,
    });

    expect(bootstrapWorkbook(workbook, { dryRun: false })).toEqual({
      dryRun: false,
      actions: [],
      changed: false,
    });
  });

  it("previews and applies the exact empty legacy migration", () => {
    const workbook = new InMemoryWorkbook({
      ...legacySeed(),
      OperatorNotes: {
        headers: ["note"],
        rows: [{ note: "must survive" }],
      },
    });
    const preview = migrateToCompactWorkbook(workbook, { dryRun: true });
    expect(preview.blockers).toEqual([]);
    expect(
      preview.actions.filter(
        (action) => action.type === "DELETE_EMPTY_LEGACY_SHEET",
      ),
    ).toHaveLength(LEGACY_FULL_SCHEMA_SHEETS.length);
    expect(workbook.getSheet("Users")).not.toBeNull();
    expect(workbook.getSheet("Overview")).toBeNull();

    const applied = migrateToCompactWorkbook(workbook, { dryRun: false });
    expect(applied.blockers).toEqual([]);
    expect(workbook.getSheet("Users")).toBeNull();
    expect(workbook.getSheet("Settings")).toBeNull();
    expect(workbook.getSheet("OperatorNotes")?.rows).toEqual([
      { note: "must survive" },
    ]);
    for (const name of expectedSheets)
      expect(workbook.getSheet(name)).not.toBeNull();
    expect(migrateToCompactWorkbook(workbook, { dryRun: false })).toEqual({
      dryRun: false,
      actions: [],
      blockers: [],
      changed: false,
    });
  });

  it("performs no mutation when any legacy data row is unknown", () => {
    const workbook = new InMemoryWorkbook({
      ...legacySeed(),
      Posts: {
        headers: ["messageId", "body"],
        rows: [{ messageId: "fixture", body: "do not delete" }],
      },
    });
    const before = [...workbook.sheets.keys()];
    const result = migrateToCompactWorkbook(workbook, { dryRun: false });
    expect(result.actions).toEqual([]);
    expect(result.blockers).toEqual(["Posts contains 1 data row(s)"]);
    expect([...workbook.sheets.keys()]).toEqual(before);
    expect(workbook.getSheet("Overview")).toBeNull();
    expect(workbook.getSheet("Posts")?.rows).toHaveLength(1);
  });

  it("blocks migration when legacy Settings has an operator-owned key", () => {
    const seed = legacySeed();
    seed.Settings?.rows?.push({
      settingKey: "operator.note",
      settingValue: "preserve",
    });
    const workbook = new InMemoryWorkbook(seed);
    const result = migrateToCompactWorkbook(workbook, { dryRun: true });
    expect(result.actions).toEqual([]);
    expect(result.blockers).toEqual([
      "Settings contains operator-owned keys: operator.note",
    ]);
  });
});
