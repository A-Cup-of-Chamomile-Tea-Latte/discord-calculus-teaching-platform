export type AnalysisDecision = "INCLUDED" | "EXCLUDED";
export type AnalysisDecisionSource = "DATABASE";

export interface CaseAnalysisState {
  originalPosterDecision: AnalysisDecision;
  source: AnalysisDecisionSource;
}

export interface MessageAnalysisContext {
  isOriginalPoster: boolean;
  authorDecision: AnalysisDecision | "INHERIT";
}

export interface AnalysisEligibilityResult {
  caseEligible: boolean;
  messageEligible: boolean;
  projectionMarker: "AI✓" | "AI×";
  source: AnalysisDecisionSource;
}

/** Database state is authoritative; a Discord title/tag is output only. */
export function evaluateAnalysisEligibility(
  state: CaseAnalysisState,
  message: MessageAnalysisContext,
): AnalysisEligibilityResult {
  if (state.source !== "DATABASE") {
    throw new Error("ANALYSIS_DECISION_MUST_COME_FROM_DATABASE");
  }
  if (state.originalPosterDecision === "EXCLUDED") {
    return {
      caseEligible: false,
      messageEligible: false,
      projectionMarker: "AI×",
      source: "DATABASE",
    };
  }

  const messageEligible =
    message.isOriginalPoster || message.authorDecision !== "EXCLUDED";
  return {
    caseEligible: true,
    messageEligible,
    projectionMarker: "AI✓",
    source: "DATABASE",
  };
}
