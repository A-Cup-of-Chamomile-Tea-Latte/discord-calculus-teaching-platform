import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { CaseRecord, Clock } from "./contracts";
import {
  FixtureCaseRepository,
  FixtureFollowUpProvider,
  FixtureRefreshProvider,
  MemoryCaseAuditSink,
} from "./fixture-providers";
import { CaseService } from "./service";

class FixedClock implements Clock {
  now(): string {
    return "2026-07-03T12:10:00+08:00";
  }
}

function createService(records?: CaseRecord[]): {
  service: CaseService;
  audit: MemoryCaseAuditSink;
} {
  const audit = new MemoryCaseAuditSink();
  return {
    service: new CaseService({
      repository: new FixtureCaseRepository(records),
      refreshProvider: new FixtureRefreshProvider(),
      followUpProvider: new FixtureFollowUpProvider(),
      auditSink: audit,
      clock: new FixedClock(),
    }),
    audit,
  };
}

describe("fixture-first GAS case service", () => {
  it("normalizes and returns only the CaseLookupResponse public projection", () => {
    const { service } = createService();
    expect(service.lookup(" c01 - 7k4m2q - 0702 - 1000 ")).toEqual({
      schemaVersion: "1.0",
      requestedCaseNumber: "C01-7K4M2Q-0702-1000",
      outcome: "FOUND",
      case: {
        caseNumber: "C01-7K4M2Q-0702-1000",
        caseType: "GENERAL",
        status: "OPEN",
        visibility: "COURSE",
        publicSummary: "Fictional limit step question",
        updatedAt: "2026-07-02T10:12:00+08:00",
      },
      lookedUpAt: "2026-07-03T12:10:00+08:00",
    });
  });

  it("covers malformed, missing, and unknown case numbers", () => {
    const { service } = createService();
    expect(service.lookup("").outcome).toBe("INVALID");
    expect(service.lookup("421").outcome).toBe("INVALID");
    expect(service.lookup("C01-7K4M2Q-0002-1000").outcome).toBe("INVALID");
    expect(service.lookup("C01-7K4M2Q-0230-1000").outcome).toBe("INVALID");
    expect(service.lookup("C01-7K4M2Q-0702-2400").outcome).toBe("INVALID");
    expect(service.lookup("C01-7K4M2Q-0702-1260").outcome).toBe("INVALID");
    expect(service.lookup("C01-Z8Y7X6-0703-2359").outcome).toBe("NOT_FOUND");
  });

  it("does not reveal Private Support through a public lookup or list", () => {
    const { service } = createService();
    expect(service.lookup("C99-B4W9K6-0702-1500-P")).toMatchObject({
      outcome: "NOT_FOUND",
      case: null,
    });
    expect(JSON.stringify(service.listPublic())).not.toMatch(
      /PRIVATE_SUPPORT|case_private_001/,
    );
  });

  it("returns NOT_PUBLIC for a well-formed staff-only general case", () => {
    const staffOnly: CaseRecord = {
      caseId: "case_staff_only",
      caseNumber: "C88-Z8Y7X6-0703-0000",
      caseType: "GENERAL",
      status: "ESCALATED",
      visibility: "TEACHING_STAFF",
      title: "Fixture staff-only case",
      updatedAt: "2026-07-03T00:00:00+08:00",
    };
    const { service } = createService([staffOnly]);
    expect(service.lookup("C88-Z8Y7X6-0703-0000")).toMatchObject({
      outcome: "NOT_PUBLIC",
      case: null,
    });
  });

  it("uses explicit refresh and never starts polling", () => {
    const { service } = createService();
    expect(service.requestRefresh("C01-7K4M2Q-0702-1000")).toEqual({
      ok: true,
      accepted: false,
      outcome: "NO_OP",
      polling: false,
    });
    const source = readFileSync(
      new URL("./service.ts", import.meta.url),
      "utf8",
    );
    expect(source).not.toMatch(/setInterval|setTimeout/);
  });

  it("keeps follow-up as a non-persisting placeholder with anonymous mediation", () => {
    const { service } = createService();
    expect(
      service.submitFollowUp({
        caseNumber: "C01-7K4M2Q-0702-1000",
        content: "Fictional follow-up content",
        authorDisplayMode: "ANONYMOUS",
      }),
    ).toEqual({
      ok: false,
      accepted: false,
      outcome: "NOT_CONFIGURED",
      persisted: false,
      anonymousMediationRequired: true,
    });
  });

  it("audits only route/outcome metadata, not case number or content", () => {
    const { service, audit } = createService();
    service.lookup("C01-7K4M2Q-0702-1000");
    service.submitFollowUp({
      caseNumber: "C01-7K4M2Q-0702-1000",
      content: "Fictional follow-up content",
      authorDisplayMode: "COURSE_ALIAS",
    });
    expect(audit.events.length).toBeGreaterThanOrEqual(3);
    expect(JSON.stringify(audit.events)).not.toMatch(
      /C01-7K4M2Q-0702-1000|Fictional follow-up|caseId|userId/,
    );
    expect(Object.keys(audit.events[0] ?? {}).sort()).toEqual([
      "eventType",
      "occurredAt",
      "outcome",
      "route",
    ]);
  });
});
