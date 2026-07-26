export type CaseStatus =
  | "OPEN"
  | "WAITING_FOR_STUDENT"
  | "ANSWERED"
  | "ESCALATED"
  | "TEMPORARILY_CLOSED"
  | "CLOSED"
  | "REOPENED";
export type PublicVisibility = "CLASS" | "COURSE";
export type AuthorDisplayMode = "REAL_NAME" | "COURSE_ALIAS" | "ANONYMOUS";

export interface PublicAttachment {
  filename: string;
  mediaType: string;
  sizeBytes: number;
}

export type TimelineEventType =
  | "SUBMITTED"
  | "TEACHING_RESPONSE"
  | "STUDENT_FOLLOW_UP"
  | "ANSWERED"
  | "ESCALATED"
  | "VERIFIED_VIEW"
  | "TEMPORARILY_CLOSED"
  | "CLOSED"
  | "REOPENED";

export interface PublicTimelineEvent {
  eventType: TimelineEventType;
  occurredAt: string;
  label: string;
}

export interface PublicMessage {
  sequence: number;
  replyToSequence: number | null;
  authorLabel: string;
  authorRole: "STUDENT" | "TA" | "INSTRUCTOR" | "BOT";
  body: string;
  createdAt: string;
  editedAt: string | null;
  attachments: PublicAttachment[];
}

export interface PublicCaseView {
  caseNumber: string;
  title: string;
  status: CaseStatus;
  visibility: PublicVisibility;
  authorDisplayMode: AuthorDisplayMode;
  updatedAt: string;
  lastUpdateAt: string;
  lastTeachingResponseAt: string | null;
  lastStudentActivityAt: string | null;
  lastReadAt: string | null;
  lastSyncedAt: string;
  latestTeachingResponseExcerpt: string | null;
  attachmentCount: number;
  hasAttachments: boolean;
  timelineEvents: PublicTimelineEvent[];
  discordDeepLink: string | null;
  closureSource: "MANUAL" | "AUTO" | null;
  closedAt: string | null;
  reopenedAt: string | null;
  analysisEligibility: "ELIGIBLE" | "EXCLUDED";
  analysisDecisionSource: "DATABASE";
  latestTeachingResponse: PublicMessage | null;
  messages: PublicMessage[];
}

export type LookupResult =
  | { outcome: "FOUND"; normalizedCaseNumber: string; case: PublicCaseView }
  | { outcome: "NOT_FOUND"; normalizedCaseNumber: string; case: null }
  | { outcome: "INVALID"; normalizedCaseNumber: string; case: null };

export interface CaseLookupAdapter {
  lookup(caseNumber: string): Promise<LookupResult>;
  listPublicCases(): Promise<PublicCaseView[]>;
}

export function normalizeCaseNumber(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

export function isCaseNumberWellFormed(value: string): boolean {
  const match =
    /^C[0-9]{2}-[A-HJ-NP-Z2-9]{6}-([0-9]{2})([0-9]{2})-([0-9]{2})([0-9]{2})(?:-P)?$/.exec(
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
