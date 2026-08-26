import rawCases from "../../../../fixtures/cases/cases.json";
import rawProjections from "../../../../fixtures/cases/case-projections.json";
import rawMemberships from "../../../../fixtures/users/course-memberships.json";
import rawMessages from "../../../../fixtures/messages/case-000421-thread.json";
import rawUsers from "../../../../fixtures/users/users.json";

import type {
  AuthorDisplayMode,
  CaseLookupAdapter,
  CaseStatus,
  CaseStatusView,
  LookupResult,
  PublicCaseView,
  PublicMessage,
  PublicTimelineEvent,
  PublicVisibility,
} from "./case-adapter";
import {
  isCaseNumberWellFormed,
  normalizeCaseNumber,
  toCaseStatusView,
} from "./case-adapter";

type ProjectionTimelineEventType =
  PublicTimelineEvent["eventType"] | "VERIFIED_VIEW";

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
  timelineEvents: Array<
    Omit<PublicTimelineEvent, "eventType"> & {
      eventType: ProjectionTimelineEventType;
    }
  >;
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

const publicFixtureTitles: Record<string, string> = {
  case_000421: "極限步驟提問",
  case_000422: "連續性提問",
  case_000423: "導數記號提問",
  case_000424: "定理解讀提問",
  case_000425: "積分設定提問",
};

const publicFixtureMessageBodies: Record<string, string> = {
  msg_000421_a: "這一步為什麼可以先做因式分解，再代入極限？",
  msg_000421_b: "你先嘗試拆出哪一個共同因式？",
  msg_000421_c: "我補上了一張示意圖，也修正了前一則訊息中的算式。",
  msg_000421_d: "先把共同因式約掉，再代入極限值，就能避開原本的未定形。",
};

const publicTimeline = (
  events: FixtureProjection["timelineEvents"],
  closureSource: FixtureProjection["closureSource"],
): PublicTimelineEvent[] => {
  const eventCopy: Record<
    ProjectionTimelineEventType,
    { eventType: PublicTimelineEvent["eventType"]; label: string }
  > = {
    SUBMITTED: { eventType: "SUBMITTED", label: "已建立案件" },
    TEACHING_RESPONSE: {
      eventType: "TEACHING_RESPONSE",
      label: "教學團隊已回覆",
    },
    STUDENT_FOLLOW_UP: {
      eventType: "STUDENT_FOLLOW_UP",
      label: "學生已補充內容",
    },
    TRACKED: { eventType: "TRACKED", label: "教學團隊處理中" },
    IDLE: { eventType: "IDLE", label: "已寄出未回覆提醒" },
    CLOSED: {
      eventType: closureSource === "AUTO" ? "AUTO_CLOSED" : "CLOSED",
      label: closureSource === "AUTO" ? "已自動結案" : "負責人已結案",
    },
    AUTO_CLOSED: { eventType: "AUTO_CLOSED", label: "已自動結案" },
    REOPENED: { eventType: "REOPENED", label: "已重新開啟" },
    VERIFIED_VIEW: { eventType: "TRACKED", label: "已查看最新回覆" },
  };
  return events.map((event) => ({
    ...event,
    ...eventCopy[event.eventType],
  }));
};

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
    body: publicFixtureMessageBodies[message.messageId] ?? message.body,
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
    title: publicFixtureTitles[item.caseId] ?? item.title,
    status: reducedProjection.status,
    visibility: item.visibility as PublicVisibility,
    authorDisplayMode: item.authorDisplayMode,
    updatedAt: reducedProjection.lastUpdateAt,
    lastUpdateAt: reducedProjection.lastUpdateAt,
    lastTeachingResponseAt: reducedProjection.lastTeachingResponseAt,
    lastStudentActivityAt: reducedProjection.lastStudentActivityAt,
    lastReadAt: reducedProjection.lastReadAt,
    lastSyncedAt: reducedProjection.lastSyncedAt,
    latestTeachingResponseExcerpt: latestTeachingResponse?.body ?? null,
    attachmentCount: reducedProjection.attachmentCount,
    hasAttachments: reducedProjection.hasAttachments,
    timelineEvents: publicTimeline(
      reducedProjection.timelineEvents,
      reducedProjection.closureSource,
    ),
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

  async listCaseStatuses(): Promise<CaseStatusView[]> {
    return cases.flatMap((item) => {
      if (!item.caseNumber) return [];
      const publicCase = toPublicCase(item);
      if (publicCase) return [toCaseStatusView(publicCase)];
      if (item.caseType !== "PRIVATE_SUPPORT") return [];
      return [
        {
          caseNumber: item.caseNumber,
          caseType: "PRIVATE_SUPPORT",
          status: item.status,
          updatedAt: item.updatedAt,
          teachingTeamReplied: false,
          discordDeepLink: null,
        },
      ];
    });
  }
}

export const fixtureCaseLookupAdapter = new FixtureCaseLookupAdapter();
