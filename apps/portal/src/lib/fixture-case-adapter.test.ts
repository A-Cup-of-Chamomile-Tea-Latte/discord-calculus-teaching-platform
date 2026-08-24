import { describe, expect, it } from "vitest";

import { FixtureCaseLookupAdapter } from "./fixture-case-adapter";

describe("FixtureCaseLookupAdapter", () => {
  const adapter = new FixtureCaseLookupAdapter();

  it("returns the shared public case without Discord IDs", async () => {
    const result = await adapter.lookup(" c01-7k4m2q-0702-1000 ");
    expect(result.outcome).toBe("FOUND");
    expect(JSON.stringify(result)).not.toContain("223456789012345678");
  });

  it("does not expose Private Support", async () => {
    const listed = await adapter.listPublicCases();
    expect(listed).toHaveLength(5);
    expect(listed.every((item) => item.caseNumber.startsWith("C"))).toBe(true);
    expect(listed.every((item) => !item.title.includes("Fictional"))).toBe(
      true,
    );
    expect(JSON.stringify(listed)).not.toContain("case_private_001");
  });

  it("exposes only a reduced private status through the status lookup list", async () => {
    const statuses = await adapter.listCaseStatuses();
    const privateStatus = statuses.find(
      (item) => item.caseType === "PRIVATE_SUPPORT",
    );
    expect(privateStatus).toEqual({
      caseNumber: "C99-B4W9K6-0702-1500-P",
      caseType: "PRIVATE_SUPPORT",
      status: "OPEN",
      updatedAt: "2026-07-02T15:00:00+08:00",
      teachingTeamReplied: false,
      discordDeepLink: null,
    });
    expect(JSON.stringify(privateStatus)).not.toMatch(
      /title|message|attachment|author|analysis|discordMapping/i,
    );
  });

  it("returns a complete reduced projection with safe attachment markers", async () => {
    const result = await adapter.lookup("C01-7K4M2Q-0702-1000");
    expect(result.outcome).toBe("FOUND");
    if (result.outcome !== "FOUND") return;
    expect(result.case).toMatchObject({
      lastUpdateAt: "2026-07-02T10:12:00+08:00",
      lastTeachingResponseAt: "2026-07-02T10:12:00+08:00",
      lastStudentActivityAt: "2026-07-02T10:08:00+08:00",
      lastReadAt: "2026-07-02T10:16:00+08:00",
      lastSyncedAt: "2026-07-02T10:15:00+08:00",
      attachmentCount: 1,
      hasAttachments: true,
      analysisDecisionSource: "DATABASE",
    });
    expect(result.case.timelineEvents).toHaveLength(4);
    expect(result.case.discordDeepLink).toMatch(
      /^https:\/\/discord\.com\/channels\//,
    );
  });

  it("keeps the Private -P fixture out of public lookup", async () => {
    await expect(
      adapter.lookup("C99-B4W9K6-0702-1500-P"),
    ).resolves.toMatchObject({ outcome: "NOT_FOUND", case: null });
  });

  it("rejects malformed case numbers", async () => {
    await expect(adapter.lookup("not a case")).resolves.toMatchObject({
      outcome: "INVALID",
    });
  });
});
