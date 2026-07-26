import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { bootstrapWorkbook } from "./bootstrap";
import { InMemoryWorkbook } from "./in-memory-workbook";
import {
  headersFor,
  SCHEMA_METADATA_ROWS,
  SHEET_SCHEMAS,
  SHEETS_SCHEMA_VERSION,
} from "./schema";

const expectedSheets = [
  "Users",
  "Emails",
  "DiscordAccounts",
  "CourseMemberships",
  "Cases",
  "Posts",
  "Consents",
  "ActiveCases",
  "CaseProjection",
  "SyncState",
  "ChangedCaseQueue",
  "ArchiveIndex",
  "ExportManifest",
  "SanitizedPackage",
  "WeeklyMaintenanceRun",
  "ActivationCodes",
  "Exports",
  "AuditLog",
  "Settings",
];

describe("Sheets schema", () => {
  it("defines all required sheets with unique headers and primary keys", () => {
    expect(SHEET_SCHEMAS.map((sheet) => sheet.name)).toEqual(expectedSheets);
    for (const sheet of SHEET_SCHEMAS) {
      const headers = headersFor(sheet);
      expect(new Set(headers).size).toBe(headers.length);
      expect(headers).toContain(sheet.primaryKey);
      expect(sheet.indexes.length).toBeGreaterThan(0);
      expect(sheet.retention.length).toBeGreaterThan(20);
      expect(sheet.sourceContracts.length).toBeGreaterThan(0);
    }
  });

  it("stores only an activation verifier hash, never a plaintext nonce", () => {
    const activation = SHEET_SCHEMAS.find(
      (sheet) => sheet.name === "ActivationCodes",
    );
    expect(activation).toBeDefined();
    expect(headersFor(activation!)).toContain("verifierHash");
    expect(headersFor(activation!)).not.toContain("plaintextCode");
    expect(headersFor(activation!)).not.toContain("nonce");

    const seedText = readFileSync(
      new URL("../../fixtures/sheets-seed.json", import.meta.url),
      "utf8",
    );
    expect(seedText).toContain('"verifierHash": "sha256:');
    expect(seedText).not.toMatch(/"(?:plaintextCode|nonce|secret|token)"\s*:/i);
  });

  it("keeps every fixture seed key within its sheet header contract", () => {
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

  it("produces a dry-run plan without mutating the workbook", () => {
    const workbook = new InMemoryWorkbook();
    const result = bootstrapWorkbook(workbook, { dryRun: true });
    expect(result.changed).toBe(true);
    expect(
      result.actions.filter((action) => action.type === "CREATE_SHEET"),
    ).toHaveLength(expectedSheets.length);
    expect(workbook.sheets.size).toBe(0);
  });

  it("applies the schema and becomes idempotent on the second run", () => {
    const workbook = new InMemoryWorkbook();
    const first = bootstrapWorkbook(workbook, { dryRun: false });
    expect(first.changed).toBe(true);
    expect([...workbook.sheets.keys()]).toEqual(expectedSheets);
    for (const definition of SHEET_SCHEMAS) {
      expect(workbook.getSheet(definition.name)?.getHeaders()).toEqual(
        headersFor(definition),
      );
    }
    const settings = workbook.getSheet("Settings");
    expect(settings?.rows).toHaveLength(SCHEMA_METADATA_ROWS.length);
    expect(settings?.rows[0]).toMatchObject({
      settingKey: "schema.version",
      settingValue: SHEETS_SCHEMA_VERSION,
    });

    const second = bootstrapWorkbook(workbook, { dryRun: false });
    expect(second).toEqual({ dryRun: false, actions: [], changed: false });
  });

  it("appends missing headers without deleting extra headers or rows", () => {
    const workbook = new InMemoryWorkbook({
      Users: {
        headers: ["legacyNote", "userId"],
        rows: [{ legacyNote: "keep me", userId: "usr_fixture" }],
      },
    });
    bootstrapWorkbook(workbook, { dryRun: false });
    const users = workbook.getSheet("Users");
    expect(users?.headers.slice(0, 2)).toEqual(["legacyNote", "userId"]);
    expect(users?.headers).toContain("schemaVersion");
    expect(users?.rows).toEqual([
      { legacyNote: "keep me", userId: "usr_fixture" },
    ]);
  });

  it("upgrades only managed schema metadata when its value is stale", () => {
    const workbook = new InMemoryWorkbook({
      Settings: {
        headers: ["settingKey", "settingValue", "description", "updatedAt"],
        rows: [
          {
            settingKey: "schema.version",
            settingValue: "0.9.0",
            description: "old",
            updatedAt: "2026-01-01T00:00:00+08:00",
          },
          { settingKey: "operator.note", settingValue: "preserve" },
        ],
      },
    });
    const result = bootstrapWorkbook(workbook, { dryRun: false });
    expect(result.actions).toContainEqual({
      type: "UPSERT_SCHEMA_METADATA",
      sheet: "Settings",
      settingKey: "schema.version",
      change: "update",
    });
    expect(
      workbook
        .getSheet("Settings")
        ?.getRowByPrimaryKey("settingKey", "operator.note"),
    ).toEqual({ settingKey: "operator.note", settingValue: "preserve" });
  });
});
