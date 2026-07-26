import type {
  CaseLookupAdapter,
  CaseStatus,
  LookupResult,
  PublicCaseView,
  PublicVisibility,
} from "./case-adapter";
import { isCaseNumberWellFormed, normalizeCaseNumber } from "./case-adapter";

export interface GasPublicCaseSummary {
  caseNumber: string;
  caseType: "GENERAL";
  status: CaseStatus;
  visibility: PublicVisibility;
  publicSummary: string;
  updatedAt: string;
}

export interface GasCaseLookupResponse {
  schemaVersion: "1.0";
  requestedCaseNumber: string;
  outcome: "FOUND" | "NOT_FOUND" | "NOT_PUBLIC" | "INVALID";
  case: GasPublicCaseSummary | null;
  lookedUpAt: string;
}

export interface GasCaseApiTransport {
  lookup(caseNumber: string): Promise<GasCaseLookupResponse>;
  listPublicCases(): Promise<GasCaseLookupResponse[]>;
}

const responseKeys = [
  "schemaVersion",
  "requestedCaseNumber",
  "outcome",
  "case",
  "lookedUpAt",
] as const;
const caseKeys = [
  "caseNumber",
  "caseType",
  "status",
  "visibility",
  "publicSummary",
  "updatedAt",
] as const;

function hasOnlyKeys(
  value: Record<string, unknown>,
  allowed: readonly string[],
): boolean {
  return Object.keys(value).every((key) => allowed.includes(key));
}

function assertSafeResponse(response: GasCaseLookupResponse): void {
  if (
    !hasOnlyKeys(response as unknown as Record<string, unknown>, responseKeys)
  ) {
    throw new Error("INVALID_GAS_CASE_RESPONSE");
  }
  if (
    response.case &&
    !hasOnlyKeys(response.case as unknown as Record<string, unknown>, caseKeys)
  ) {
    throw new Error("INVALID_GAS_CASE_PROJECTION");
  }
  if (
    response.outcome === "FOUND"
      ? response.case === null
      : response.case !== null
  ) {
    throw new Error("INCONSISTENT_GAS_CASE_RESPONSE");
  }
}

function toPortalCase(summary: GasPublicCaseSummary): PublicCaseView {
  return {
    caseNumber: summary.caseNumber,
    title: summary.publicSummary,
    status: summary.status,
    visibility: summary.visibility,
    authorDisplayMode: "ANONYMOUS",
    updatedAt: summary.updatedAt,
    lastUpdateAt: summary.updatedAt,
    lastTeachingResponseAt: null,
    lastStudentActivityAt: null,
    lastReadAt: null,
    lastSyncedAt: summary.updatedAt,
    latestTeachingResponseExcerpt: null,
    attachmentCount: 0,
    hasAttachments: false,
    timelineEvents: [],
    discordDeepLink: null,
    closureSource: summary.status === "CLOSED" ? "MANUAL" : null,
    closedAt: summary.status === "CLOSED" ? summary.updatedAt : null,
    reopenedAt: null,
    analysisEligibility: "EXCLUDED",
    analysisDecisionSource: "DATABASE",
    latestTeachingResponse: null,
    messages: [],
  };
}

export class GasCaseLookupAdapter implements CaseLookupAdapter {
  constructor(private readonly transport: GasCaseApiTransport) {}

  async lookup(caseNumber: string): Promise<LookupResult> {
    const normalizedCaseNumber = normalizeCaseNumber(caseNumber);
    if (!isCaseNumberWellFormed(normalizedCaseNumber)) {
      return { outcome: "INVALID", normalizedCaseNumber, case: null };
    }
    const response = await this.transport.lookup(normalizedCaseNumber);
    assertSafeResponse(response);
    if (response.outcome === "INVALID") {
      return { outcome: "INVALID", normalizedCaseNumber, case: null };
    }
    if (response.outcome !== "FOUND" || response.case === null) {
      return { outcome: "NOT_FOUND", normalizedCaseNumber, case: null };
    }
    return {
      outcome: "FOUND",
      normalizedCaseNumber,
      case: toPortalCase(response.case),
    };
  }

  async listPublicCases(): Promise<PublicCaseView[]> {
    const responses = await this.transport.listPublicCases();
    return responses.flatMap((response) => {
      assertSafeResponse(response);
      return response.outcome === "FOUND" && response.case
        ? [toPortalCase(response.case)]
        : [];
    });
  }
}
