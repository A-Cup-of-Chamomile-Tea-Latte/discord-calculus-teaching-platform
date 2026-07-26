import { describe, expect, it } from "vitest";

import { evaluateAnalysisEligibility } from "./analysis-eligibility";

describe("case-level AI eligibility", () => {
  it("excludes the entire case when the original poster selects No", () => {
    expect(
      evaluateAnalysisEligibility(
        { originalPosterDecision: "EXCLUDED", source: "DATABASE" },
        { isOriginalPoster: false, authorDecision: "INCLUDED" },
      ),
    ).toEqual({
      caseEligible: false,
      messageEligible: false,
      projectionMarker: "AI×",
      source: "DATABASE",
    });
  });

  it("keeps a per-author message filter when the original poster selects Yes", () => {
    const state = {
      originalPosterDecision: "INCLUDED" as const,
      source: "DATABASE" as const,
    };
    expect(
      evaluateAnalysisEligibility(state, {
        isOriginalPoster: false,
        authorDecision: "EXCLUDED",
      }),
    ).toMatchObject({ caseEligible: true, messageEligible: false });
    expect(
      evaluateAnalysisEligibility(state, {
        isOriginalPoster: false,
        authorDecision: "INHERIT",
      }),
    ).toMatchObject({ caseEligible: true, messageEligible: true });
  });

  it("refuses a Discord marker as an authoritative decision source", () => {
    expect(() =>
      evaluateAnalysisEligibility(
        {
          originalPosterDecision: "INCLUDED",
          source: "DISCORD_TAG" as "DATABASE",
        },
        { isOriginalPoster: true, authorDecision: "INHERIT" },
      ),
    ).toThrow("ANALYSIS_DECISION_MUST_COME_FROM_DATABASE");
  });
});
