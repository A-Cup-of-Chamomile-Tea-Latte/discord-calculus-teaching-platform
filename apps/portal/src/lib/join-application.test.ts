import { describe, expect, it } from "vitest";

import {
  canManageJoinReviewers,
  canReviewJoinApplication,
  duplicateApplicationDm,
  joinApplicantKey,
  nextJoinApplicationStatus,
} from "./join-application";

describe("join application policy", () => {
  it("deduplicates without treating the academic term as identity", () => {
    expect(
      joinApplicantKey({
        identityType: "STUDENT",
        discordUsername: "DingDing124816",
        ntuEmail: "STUDENT@NTU.EDU.TW",
      }),
    ).toBe("STUDENT:student@ntu.edu.tw:dingding124816");
    expect(
      joinApplicantKey({
        identityType: "STUDENT",
        discordUsername: "changed-name",
        ntuEmail: "student@ntu.edu.tw",
        discordUserId: "synthetic-discord-id",
      }),
    ).toBe("discord:synthetic-discord-id");
    expect(duplicateApplicationDm).toContain("你已經註冊過了呦");
  });

  it("keeps member-not-found applications instead of rejecting them", () => {
    expect(
      nextJoinApplicationStatus("PENDING_REVIEW", "MEMBER_NOT_FOUND"),
    ).toBe("WAITING_FOR_DISCORD_MEMBER");
    expect(
      nextJoinApplicationStatus("WAITING_FOR_DISCORD_MEMBER", "APPROVE"),
    ).toBe("APPROVED");
  });

  it("lets teaching reviewers decide applications but only admins manage reviewers", () => {
    expect(canReviewJoinApplication("TEACHING_REVIEWER")).toBe(true);
    expect(canManageJoinReviewers("TEACHING_REVIEWER")).toBe(false);
    expect(canManageJoinReviewers("SYSTEM_ADMIN")).toBe(true);
  });

  it("archives reversibly", () => {
    expect(nextJoinApplicationStatus("REJECTED", "ARCHIVE")).toBe("ARCHIVED");
    expect(nextJoinApplicationStatus("ARCHIVED", "RESTORE")).toBe(
      "PENDING_REVIEW",
    );
  });
});
