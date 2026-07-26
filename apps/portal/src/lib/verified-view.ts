export interface VerifiedViewEvidence {
  caseId: string;
  verifiedAt: string;
  method: "VERIFIED_VIEW";
  evidenceId: string;
}

/**
 * Boundary for a future approved verification method. A Portal page load must
 * never be treated as evidence by itself.
 */
export interface VerifiedViewProvider {
  latestForCase(caseId: string): Promise<VerifiedViewEvidence | null>;
}

export class FixtureVerifiedViewProvider implements VerifiedViewProvider {
  constructor(private readonly evidence: readonly VerifiedViewEvidence[]) {}

  async latestForCase(caseId: string): Promise<VerifiedViewEvidence | null> {
    return (
      this.evidence
        .filter((item) => item.caseId === caseId)
        .sort((left, right) =>
          right.verifiedAt.localeCompare(left.verifiedAt),
        )[0] ?? null
    );
  }
}
