import { describe, expect, it } from "vitest";

import {
  canManageJoinReviewers,
  canReviewJoinApplication,
  discordInviteUrl,
  duplicateApplicationDm,
  joinApplicantKey,
  nextJoinApplicationStatus,
  sameOriginEndpointPath,
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

  it("accepts only same-origin endpoint paths", () => {
    expect(sameOriginEndpointPath("/api/join")).toBe("/api/join");
    expect(
      sameOriginEndpointPath(" https://example.com/api/join "),
    ).toBeUndefined();
    expect(sameOriginEndpointPath("//example.com/api/join")).toBeUndefined();
    expect(sameOriginEndpointPath("/api\\join")).toBeUndefined();
  });

  it("accepts only official Discord invite URLs", () => {
    expect(discordInviteUrl("https://discord.gg/course-room")).toBe(
      "https://discord.gg/course-room",
    );
    expect(discordInviteUrl("https://discord.com/invite/course_room")).toBe(
      "https://discord.com/invite/course_room",
    );
    expect(discordInviteUrl("http://discord.gg/course-room")).toBeUndefined();
    expect(discordInviteUrl("https://example.com/course-room")).toBeUndefined();
    expect(
      discordInviteUrl("https://discord.gg/course-room?tracking=1"),
    ).toBeUndefined();
  });
});
