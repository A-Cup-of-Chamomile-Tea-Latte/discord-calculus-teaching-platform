import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { toCaseStatusView } from "./case-adapter";
import { lookupCaseStatus, lookupPublicCase } from "./client-case-lookup";
import { FixtureCaseLookupAdapter } from "./fixture-case-adapter";

describe("offline public case lookup", () => {
  const adapter = new FixtureCaseLookupAdapter();

  it("normalizes case and whitespace for a found case", async () => {
    const cases = await adapter.listPublicCases();
    const result = lookupPublicCase(cases, "  c01 - 7k4m2q - 0702 - 1000  ");
    expect(result).toMatchObject({
      outcome: "FOUND",
      normalizedCaseNumber: "C01-7K4M2Q-0702-1000",
    });
  });

  it("returns a clear not-found outcome", async () => {
    const cases = await adapter.listPublicCases();
    expect(lookupPublicCase(cases, "C01-Z9Y8X7-0702-2359").outcome).toBe(
      "NOT_FOUND",
    );
  });

  it("rejects malformed input before lookup", async () => {
    const cases = await adapter.listPublicCases();
    expect(lookupPublicCase(cases, "421").outcome).toBe("INVALID");
  });

  it.each([
    "C01-7K4M2Q-0002-1000",
    "C01-7K4M2Q-1331-1000",
    "C01-7K4M2Q-0230-1000",
    "C01-7K4M2Q-0702-2400",
    "C01-7K4M2Q-0702-1260",
  ])("rejects an impossible date or time: %s", async (caseNumber) => {
    const cases = await adapter.listPublicCases();
    expect(lookupPublicCase(cases, caseNumber).outcome).toBe("INVALID");
  });

  it("returns the closed fixture", async () => {
    const cases = await adapter.listPublicCases();
    const result = lookupPublicCase(cases, "C02-M6X2C7-0702-1400");
    expect(result.outcome === "FOUND" && result.case.status).toBe("CLOSED");
  });

  it("returns the anonymous fixture without an identity", async () => {
    const cases = await adapter.listPublicCases();
    const result = lookupPublicCase(cases, "C02-R8N6WX-0702-1100");
    expect(result.outcome === "FOUND" && result.case.authorDisplayMode).toBe(
      "ANONYMOUS",
    );
    expect(JSON.stringify(result)).not.toContain("usr_coral");
  });

  it("does not reveal Private Support through a well-formed public query", async () => {
    const cases = await adapter.listPublicCases();
    const result = lookupPublicCase(cases, "C99-B4W9K6-0702-1500-P");
    expect(result.outcome).toBe("NOT_FOUND");
    expect(JSON.stringify(cases)).not.toContain("PRIVATE_SUPPORT");
  });

  it("uses a content-free projection for the student status widget", async () => {
    const cases = (await adapter.listPublicCases()).map(toCaseStatusView);
    const result = lookupCaseStatus(cases, "C01-7K4M2Q-0702-1000");
    expect(result.outcome).toBe("FOUND");
    if (result.outcome !== "FOUND") return;
    expect(Object.keys(result.case).sort()).toEqual(
      [
        "caseNumber",
        "caseType",
        "discordDeepLink",
        "status",
        "teachingTeamReplied",
        "updatedAt",
      ].sort(),
    );
    expect(JSON.stringify(result.case)).not.toMatch(
      /title|message|attachment|author|analysis/i,
    );
  });

  it("accepts a private-number shape without requiring a second verification code", () => {
    expect(
      lookupCaseStatus(
        [
          {
            caseNumber: "C99-B4W9K6-0702-1500-P",
            caseType: "PRIVATE_SUPPORT",
            status: "TRACKED",
            updatedAt: "2026-07-02T15:00:00+08:00",
            teachingTeamReplied: false,
            discordDeepLink: null,
          },
        ],
        "c99-b4w9k6-0702-1500-p",
      ).outcome,
    ).toBe("FOUND");
  });

  it("contains no polling timer", () => {
    const script = readFileSync(
      new URL("../scripts/case-search.ts", import.meta.url),
      "utf8",
    );
    expect(script).not.toMatch(/setInterval|setTimeout/);
  });
});
