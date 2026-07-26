import type {
  CaseAuditSink,
  CaseLookupResponse,
  CaseRecord,
  CaseRepository,
  Clock,
  FollowUpProvider,
  FollowUpRequest,
  PublicCaseSummary,
  RefreshRequestProvider,
} from "./contracts";

export interface CaseServiceDependencies {
  repository: CaseRepository;
  refreshProvider: RefreshRequestProvider;
  followUpProvider: FollowUpProvider;
  auditSink: CaseAuditSink;
  clock: Clock;
}

export function normalizeCaseNumber(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

export function isCaseNumberWellFormed(value: string): boolean {
  const match =
    /^C[0-9]{2}-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}-([0-9]{2})([0-9]{2})-([0-9]{2})([0-9]{2})(?:-P)?$/.exec(
      value,
    );
  if (!match) return false;
  const [, rawMonth, rawDay, rawHour, rawMinute] = match;
  const month = Number(rawMonth);
  const day = Number(rawDay);
  const hour = Number(rawHour);
  const minute = Number(rawMinute);
  const maximumDays = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return (
    month >= 1 &&
    month <= 12 &&
    day >= 1 &&
    day <= maximumDays[month - 1] &&
    hour >= 0 &&
    hour <= 23 &&
    minute >= 0 &&
    minute <= 59
  );
}

function toPublicSummary(record: CaseRecord): PublicCaseSummary | null {
  if (
    record.caseType !== "GENERAL" ||
    record.caseNumber === null ||
    record.visibility === "TEACHING_STAFF"
  ) {
    return null;
  }
  return {
    caseNumber: record.caseNumber,
    caseType: "GENERAL",
    status: record.status,
    visibility: record.visibility,
    publicSummary: record.title.slice(0, 280),
    updatedAt: record.updatedAt,
  };
}

export class CaseService {
  constructor(private readonly dependencies: CaseServiceDependencies) {}

  lookup(rawCaseNumber: string): CaseLookupResponse {
    const requestedCaseNumber = normalizeCaseNumber(rawCaseNumber);
    const lookedUpAt = this.dependencies.clock.now();
    let response: CaseLookupResponse;

    if (!isCaseNumberWellFormed(requestedCaseNumber)) {
      response = {
        schemaVersion: "1.0",
        requestedCaseNumber,
        outcome: "INVALID",
        case: null,
        lookedUpAt,
      };
    } else {
      const record =
        this.dependencies.repository.findByCaseNumber(requestedCaseNumber);
      if (!record || record.caseType === "PRIVATE_SUPPORT") {
        response = {
          schemaVersion: "1.0",
          requestedCaseNumber,
          outcome: "NOT_FOUND",
          case: null,
          lookedUpAt,
        };
      } else {
        const publicCase = toPublicSummary(record);
        response = {
          schemaVersion: "1.0",
          requestedCaseNumber,
          outcome: publicCase ? "FOUND" : "NOT_PUBLIC",
          case: publicCase,
          lookedUpAt,
        };
      }
    }

    this.dependencies.auditSink.record({
      eventType: "CASE_LOOKUP",
      outcome: response.outcome,
      route: "/api/cases/lookup",
      occurredAt: lookedUpAt,
    });
    return response;
  }

  listPublic(): CaseLookupResponse[] {
    return this.dependencies.repository
      .list()
      .map(toPublicSummary)
      .filter((record): record is PublicCaseSummary => record !== null)
      .map((record) => ({
        schemaVersion: "1.0",
        requestedCaseNumber: record.caseNumber,
        outcome: "FOUND",
        case: record,
        lookedUpAt: this.dependencies.clock.now(),
      }));
  }

  requestRefresh(rawCaseNumber: string): Record<string, unknown> {
    const lookup = this.lookup(rawCaseNumber);
    if (lookup.outcome !== "FOUND") {
      this.dependencies.auditSink.record({
        eventType: "CASE_REFRESH_REQUEST",
        outcome: `LOOKUP_${lookup.outcome}`,
        route: "/api/cases/refresh",
        occurredAt: this.dependencies.clock.now(),
      });
      return { ok: false, accepted: false, lookup };
    }
    const outcome = this.dependencies.refreshProvider.request(
      lookup.requestedCaseNumber,
    );
    this.dependencies.auditSink.record({
      eventType: "CASE_REFRESH_REQUEST",
      outcome,
      route: "/api/cases/refresh",
      occurredAt: this.dependencies.clock.now(),
    });
    return {
      ok: true,
      accepted: outcome === "QUEUED",
      outcome,
      polling: false,
    };
  }

  submitFollowUp(request: FollowUpRequest): Record<string, unknown> {
    const lookup = this.lookup(request.caseNumber);
    if (lookup.outcome !== "FOUND") {
      this.dependencies.auditSink.record({
        eventType: "CASE_FOLLOW_UP_REQUEST",
        outcome: `LOOKUP_${lookup.outcome}`,
        route: "/api/cases/follow-up",
        occurredAt: this.dependencies.clock.now(),
      });
      return { ok: false, accepted: false, lookup };
    }
    const content = request.content.trim();
    if (content.length < 5 || content.length > 2000) {
      this.dependencies.auditSink.record({
        eventType: "CASE_FOLLOW_UP_REQUEST",
        outcome: "INVALID_CONTENT",
        route: "/api/cases/follow-up",
        occurredAt: this.dependencies.clock.now(),
      });
      return {
        ok: false,
        accepted: false,
        error: "INVALID_FOLLOW_UP_CONTENT",
      };
    }
    const outcome = this.dependencies.followUpProvider.submit({
      ...request,
      caseNumber: lookup.requestedCaseNumber,
      content,
    });
    this.dependencies.auditSink.record({
      eventType: "CASE_FOLLOW_UP_REQUEST",
      outcome,
      route: "/api/cases/follow-up",
      occurredAt: this.dependencies.clock.now(),
    });
    return {
      ok: outcome === "ACCEPTED",
      accepted: outcome === "ACCEPTED",
      outcome,
      persisted: false,
      anonymousMediationRequired: request.authorDisplayMode === "ANONYMOUS",
    };
  }
}
