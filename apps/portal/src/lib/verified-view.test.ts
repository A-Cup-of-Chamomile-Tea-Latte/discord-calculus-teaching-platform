import { describe, expect, it } from "vitest";

import { FixtureVerifiedViewProvider } from "./verified-view";

describe("VERIFIED_VIEW boundary", () => {
  it("returns only explicit fixture evidence and never fabricates a page view", async () => {
    const provider = new FixtureVerifiedViewProvider([
      {
        caseId: "case_000421",
        verifiedAt: "2026-07-02T10:16:00+08:00",
        method: "VERIFIED_VIEW",
        evidenceId: "view_fixture_1",
      },
    ]);
    await expect(provider.latestForCase("case_000421")).resolves.toMatchObject({
      method: "VERIFIED_VIEW",
    });
    await expect(provider.latestForCase("unknown_case")).resolves.toBeNull();
  });
});
