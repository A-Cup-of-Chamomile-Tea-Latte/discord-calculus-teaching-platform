export type EmailKind = "INSTITUTIONAL" | "CONTACT";
export type EmailChallengeStatus =
  "PENDING" | "VERIFIED" | "EXPIRED" | "LOCKED";
export type Sha256Hash = `sha256:${string}`;

export interface EmailVerificationChallenge {
  challengeId: string;
  userId: string;
  email: string;
  kind: EmailKind;
  isPrimary: boolean;
  status: EmailChallengeStatus;
  codeSalt: string;
  codeHash: Sha256Hash;
  attemptsRemaining: number;
  sendCount: number;
  createdAt: string;
  updatedAt: string;
  expiresAt: string;
  resendAvailableAt: string;
  verifiedAt: string | null;
}

export interface VerifiedEmailRecord {
  schemaVersion: "1.0";
  verifiedEmailId: string;
  userId: string;
  email: string;
  kind: EmailKind;
  verifiedAt: string;
  isPrimary: boolean;
  createdAt: string;
}

export interface EmailVerificationRepository {
  findChallenge(challengeId: string): EmailVerificationChallenge | null;
  findLatestChallenge(
    userId: string,
    email: string,
    kind: EmailKind,
  ): EmailVerificationChallenge | null;
  findVerifiedByEmail(email: string): VerifiedEmailRecord | null;
  insertChallenge(challenge: EmailVerificationChallenge): void;
  saveChallenge(challenge: EmailVerificationChallenge): void;
  insertVerified(record: VerifiedEmailRecord): void;
}

export interface VerificationEmailDelivery {
  challengeId: string;
  destination: string;
  code: string;
  kind: EmailKind;
  expiresAt: string;
}

export interface VerificationEmailProvider {
  sendVerificationCode(delivery: VerificationEmailDelivery): void;
}

export interface EmailVerificationAuditEvent {
  eventType:
    | "EMAIL_VERIFICATION_STARTED"
    | "EMAIL_VERIFICATION_RESENT"
    | "EMAIL_VERIFICATION_ATTEMPTED";
  challengeId: string | null;
  outcome: string;
  occurredAt: string;
}

export interface EmailVerificationAuditSink {
  record(event: EmailVerificationAuditEvent): void;
}

export interface InstitutionalEmailPolicy {
  accepts(email: string): boolean;
}

export interface RandomBytesSource {
  bytes(length: number): Uint8Array;
}

export interface Sha256Hasher {
  hash(value: string): Sha256Hash;
}

export interface VerificationClock {
  now(): string;
}

export interface VerificationLock {
  runExclusive<T>(key: string, operation: () => T): T;
}

export interface StartVerificationInput {
  userId: string;
  email: string;
  kind: EmailKind;
  isPrimary: boolean;
}

export type StartVerificationOutcome =
  | "STARTED"
  | "RESENT"
  | "COOLDOWN"
  | "ATTEMPT_LOCKED"
  | "ALREADY_VERIFIED"
  | "SEND_LIMIT";

export interface StartVerificationResult {
  ok: boolean;
  outcome: StartVerificationOutcome;
  challengeId: string | null;
  expiresAt: string | null;
  resendAvailableAt: string | null;
}

export type VerifyCodeOutcome =
  | "VERIFIED"
  | "INVALID"
  | "NOT_FOUND"
  | "EXPIRED"
  | "LOCKED"
  | "WRONG_CODE"
  | "ALREADY_VERIFIED";

export interface VerifyCodeResult {
  ok: boolean;
  outcome: VerifyCodeOutcome;
  attemptsRemaining: number | null;
  verifiedEmail: VerifiedEmailRecord | null;
}
