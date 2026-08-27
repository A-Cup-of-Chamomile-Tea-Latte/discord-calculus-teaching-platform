export type JoinIdentityType = "STUDENT" | "GUEST";

export type JoinApplicationStatus =
  | "PENDING_REVIEW"
  | "WAITING_FOR_DISCORD_MEMBER"
  | "APPROVED"
  | "REJECTED"
  | "ARCHIVED";

export type JoinReviewerRole = "TEACHING_REVIEWER" | "SYSTEM_ADMIN";

export interface JoinApplicationIdentity {
  identityType: JoinIdentityType;
  discordUsername: string;
  ntuEmail?: string;
  guestEmail?: string;
  discordUserId?: string;
}

export interface JoinApplicationRecord extends JoinApplicationIdentity {
  applicationId: string;
  classCode?: string;
  guestReason?: string;
  status: JoinApplicationStatus;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string;
}

export const duplicateApplicationDm =
  "你已經註冊過了呦！我把目前的班級與權限整理在下面，有需要調整再回覆我就好。";

export function sameOriginEndpointPath(
  value: string | undefined,
): string | undefined {
  const path = value?.trim();
  if (!path || !path.startsWith("/") || path.startsWith("//")) return undefined;
  if (path.includes("\\") || /[\r\n]/.test(path)) return undefined;
  return path;
}

export function discordInviteUrl(value: string | undefined): string | undefined {
  const candidate = value?.trim();
  if (!candidate) return undefined;
  try {
    const url = new URL(candidate);
    const host = url.hostname.toLowerCase();
    const path = url.pathname.replace(/^\/+|\/+$/g, "");
    const inviteCode =
      host === "discord.gg"
        ? path
        : host === "discord.com" && path.startsWith("invite/")
          ? path.slice("invite/".length)
          : "";
    if (
      url.protocol !== "https:" ||
      url.port ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      !/^[A-Za-z0-9_-]{2,64}$/.test(inviteCode)
    ) {
      return undefined;
    }
    return url.href;
  } catch {
    return undefined;
  }
}

function normalized(value: string | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

export function joinApplicantKey(identity: JoinApplicationIdentity): string {
  if (identity.discordUserId) {
    return `discord:${identity.discordUserId}`;
  }
  const email =
    identity.identityType === "STUDENT"
      ? normalized(identity.ntuEmail)
      : normalized(identity.guestEmail);
  return `${identity.identityType}:${email}:${normalized(identity.discordUsername)}`;
}

export function canReviewJoinApplication(role: JoinReviewerRole): boolean {
  return role === "TEACHING_REVIEWER" || role === "SYSTEM_ADMIN";
}

export function canManageJoinReviewers(role: JoinReviewerRole): boolean {
  return role === "SYSTEM_ADMIN";
}

export function nextJoinApplicationStatus(
  current: JoinApplicationStatus,
  action: "MEMBER_NOT_FOUND" | "APPROVE" | "REJECT" | "ARCHIVE" | "RESTORE",
): JoinApplicationStatus {
  if (action === "ARCHIVE") return "ARCHIVED";
  if (action === "RESTORE" && current === "ARCHIVED") return "PENDING_REVIEW";
  if (action === "MEMBER_NOT_FOUND" && current !== "ARCHIVED") {
    return "WAITING_FOR_DISCORD_MEMBER";
  }
  if (
    action === "APPROVE" &&
    (current === "PENDING_REVIEW" || current === "WAITING_FOR_DISCORD_MEMBER")
  ) {
    return "APPROVED";
  }
  if (
    action === "REJECT" &&
    (current === "PENDING_REVIEW" || current === "WAITING_FOR_DISCORD_MEMBER")
  ) {
    return "REJECTED";
  }
  return current;
}
