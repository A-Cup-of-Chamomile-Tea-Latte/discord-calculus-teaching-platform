import rawCases from "../../../../fixtures/cases/cases.json";
import rawProjections from "../../../../fixtures/cases/case-projections.json";
import rawMemberships from "../../../../fixtures/users/course-memberships.json";
import rawMessages from "../../../../fixtures/messages/case-000421-thread.json";
import rawUsers from "../../../../fixtures/users/users.json";

import type {
  AuthorDisplayMode,
  CaseLookupAdapter,
  CaseStatus,
  LookupResult,
  PublicCaseView,
  PublicMessage,
  PublicTimelineEvent,
  PublicVisibility,
} from "./case-adapter";
import { isCaseNumberWellFormed, normalizeCaseNumber } from "./case-adapter";

interface FixtureCase {
  caseId: string;
  caseNumber: string | null;
  caseType: "GENERAL" | "PRIVATE_SUPPORT";
  status: CaseStatus;
  visibility: "CLASS" | "COURSE" | "TEACHING_STAFF";
  authorDisplayMode: AuthorDisplayMode;
  title: string;
  updatedAt: string;
}

interface FixtureMessage {
  messageId: string;
  caseId: string;
  authorUserId: string;
  authorRole: PublicMessage["authorRole"];
  authorDisplayMode: AuthorDisplayMode;
  body: string;
  parentMessageId: string | null;
  createdAt: string;
  editedAt: string | null;
  attachments: PublicMessage["attachments"];
}

interface FixtureMembership {
  userId: string;
  courseAlias: string;
}

interface FixtureUser {
  userId: string;
  displayLabel: string;
}

interface FixtureProjection {
  caseId: string;
  caseNumber: string;
  status: CaseStatus;
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
}

const cases = rawCases as FixtureCase[];
const messages = rawMessages as FixtureMessage[];
const memberships = rawMemberships as FixtureMembership[];
const users = rawUsers as FixtureUser[];
const projections = rawProjections as FixtureProjection[];

function authorLabel(message: FixtureMessage): string {
  if (message.authorRole === "TA" || message.authorRole === "INSTRUCTOR")
    return "教學團隊";
  if (message.authorRole === "BOT") return "系統代貼";
  if (message.authorDisplayMode === "ANONYMOUS") return "匿名學生";
  if (message.authorDisplayMode === "COURSE_ALIAS") {
    return (
      memberships.find((item) => item.userId === message.authorUserId)
        ?.courseAlias ?? "課程代號"
    );
  }
  return (
    users.find((item) => item.userId === message.authorUserId)?.displayLabel ??
    "學生"
  );
}

function publicMessages(caseId: string): PublicMessage[] {
  const selected = messages.filter((message) => message.caseId === caseId);
  const sequenceById = new Map(
    selected.map((message, index) => [message.messageId, index + 1]),
  );
  return selected.map((message, index) => ({
    sequence: index + 1,
    replyToSequence: message.parentMessageId
      ? (sequenceById.get(message.parentMessageId) ?? null)
      : null,
    authorLabel: authorLabel(message),
    authorRole: message.authorRole,
    body: message.body,
    createdAt: message.createdAt,
    editedAt: message.editedAt,
    attachments: message.attachments.map(
      ({ filename, mediaType, sizeBytes }) => ({
        filename,
        mediaType,
        sizeBytes,
      }),
    ),
  }));
}

function toPublicCase(item: FixtureCase): PublicCaseView | null {
  if (
    item.caseType !== "GENERAL" ||
    item.caseNumber === null ||
    item.visibility === "TEACHING_STAFF"
  ) {
    return null;
  }
  const projectedMessages = publicMessages(item.caseId);
  const reducedProjection = projections.find(
    (projection) => projection.caseId === item.caseId,
  );
  if (!reducedProjection || reducedProjection.caseNumber !== item.caseNumber) {
    throw new Error(`MISSING_OR_MISMATCHED_CASE_PROJECTION:${item.caseId}`);
  }
  const latestTeachingResponse =
    [...projectedMessages]
      .reverse()
      .find((message) =>
        ["TA", "INSTRUCTOR", "BOT"].includes(message.authorRole),
      ) ?? null;
  return {
    caseNumber: item.caseNumber,
    title: item.title,
    status: reducedProjection.status,
    visibility: item.visibility as PublicVisibility,
    authorDisplayMode: item.authorDisplayMode,
    updatedAt: reducedProjection.lastUpdateAt,
    lastUpdateAt: reducedProjection.lastUpdateAt,
    lastTeachingResponseAt: reducedProjection.lastTeachingResponseAt,
    lastStudentActivityAt: reducedProjection.lastStudentActivityAt,
    lastReadAt: reducedProjection.lastReadAt,
    lastSyncedAt: reducedProjection.lastSyncedAt,
    latestTeachingResponseExcerpt:
      reducedProjection.latestTeachingResponseExcerpt,
    attachmentCount: reducedProjection.attachmentCount,
    hasAttachments: reducedProjection.hasAttachments,
    timelineEvents: reducedProjection.timelineEvents,
    discordDeepLink: reducedProjection.discordDeepLink,
    closureSource: reducedProjection.closureSource,
    closedAt: reducedProjection.closedAt,
    reopenedAt: reducedProjection.reopenedAt,
    analysisEligibility: reducedProjection.analysisEligibility,
    analysisDecisionSource: reducedProjection.analysisDecisionSource,
    latestTeachingResponse,
    messages: projectedMessages,
  };
}

export class FixtureCaseLookupAdapter implements CaseLookupAdapter {
  async lookup(caseNumber: string): Promise<LookupResult> {
    const normalizedCaseNumber = normalizeCaseNumber(caseNumber);
    if (!isCaseNumberWellFormed(normalizedCaseNumber)) {
      return { outcome: "INVALID", normalizedCaseNumber, case: null };
    }
    const fixture = cases.find(
      (item) => item.caseNumber === normalizedCaseNumber,
    );
    const publicCase = fixture ? toPublicCase(fixture) : null;
    if (!publicCase)
      return { outcome: "NOT_FOUND", normalizedCaseNumber, case: null };
    return { outcome: "FOUND", normalizedCaseNumber, case: publicCase };
  }

  async listPublicCases(): Promise<PublicCaseView[]> {
    return cases
      .map(toPublicCase)
      .filter((item): item is PublicCaseView => item !== null);
  }
}

export const fixtureCaseLookupAdapter = new FixtureCaseLookupAdapter();
