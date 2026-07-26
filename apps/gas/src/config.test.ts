import { describe, expect, it } from "vitest";

import { loadConfig } from "./config";
import type { ScriptPropertyReader } from "./contracts";

function properties(values: Record<string, string>): ScriptPropertyReader {
  return { getProperty: (key) => values[key] ?? null };
}

describe("GAS configuration", () => {
  it("defaults to safe fixture mode without credentials", () => {
    expect(loadConfig(properties({}))).toEqual({
      environment: "fixture",
      fixtureMode: true,
      spreadsheetId: null,
    });
  });

  it("requires a spreadsheet ID before fixture mode can be disabled", () => {
    expect(() => loadConfig(properties({ FIXTURE_MODE: "false" }))).toThrow(
      "SPREADSHEET_ID",
    );
    expect(
      loadConfig(
        properties({
          FIXTURE_MODE: "false",
          SPREADSHEET_ID: "fixture-spreadsheet-id",
          APP_ENVIRONMENT: "staging",
        }),
      ),
    ).toMatchObject({ fixtureMode: false, environment: "staging" });
  });

  it("rejects ambiguous fixture flags", () => {
    expect(() => loadConfig(properties({ FIXTURE_MODE: "TRUE" }))).toThrow(
      "exactly true or false",
    );
  });
});
