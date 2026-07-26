export type CaseStatus =
  "OPEN" | "WAITING_FOR_STUDENT" | "ANSWERED" | "ESCALATED" | "CLOSED";

export type CaseVisibility = "CLASS" | "COURSE" | "TEACHING_STAFF";

export interface CaseRecord {
  caseId: string;
  caseNumber: string | null;
  caseType: "GENERAL" | "PRIVATE_SUPPORT";
  status: CaseStatus;
  visibility: CaseVisibility;
  title: string;
  updatedAt: string;
}

export interface PublicCaseSummary {
  caseNumber: string;
  caseType: "GENERAL";
  status: CaseStatus;
  visibility: "CLASS" | "COURSE";
  publicSummary: string;
  updatedAt: string;
}

export type CaseLookupOutcome =
  "FOUND" | "NOT_FOUND" | "NOT_PUBLIC" | "INVALID";

export interface CaseLookupResponse {
  schemaVersion: "1.0";
  requestedCaseNumber: string;
  outcome: CaseLookupOutcome;
  case: PublicCaseSummary | null;
  lookedUpAt: string;
}

export interface CaseRepository {
  findByCaseNumber(caseNumber: string): CaseRecord | null;
  list(): CaseRecord[];
}

export interface RefreshRequestProvider {
  request(caseNumber: string): "NO_OP" | "QUEUED";
}

export interface FollowUpRequest {
  caseNumber: string;
  content: string;
  authorDisplayMode: "REAL_NAME" | "COURSE_ALIAS" | "ANONYMOUS";
}

export interface FollowUpProvider {
  submit(request: FollowUpRequest): "NOT_CONFIGURED" | "ACCEPTED";
}

export interface CaseAuditEvent {
  eventType: "CASE_LOOKUP" | "CASE_REFRESH_REQUEST" | "CASE_FOLLOW_UP_REQUEST";
  outcome: string;
  route: string;
  occurredAt: string;
}

export interface CaseAuditSink {
  record(event: CaseAuditEvent): void;
}

export interface Clock {
  now(): string;
}
