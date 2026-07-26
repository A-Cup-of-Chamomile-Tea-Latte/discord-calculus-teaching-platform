export type Sha256Hash = `sha256:${string}`;
export type ActivationStatus = "UNUSED" | "USED" | "EXPIRED" | "REVOKED";
export type BindingKind = "NONE" | "EMAIL" | "DISCORD_USER";
export type ActivationRole = "STUDENT" | "TA" | "INSTRUCTOR" | "OBSERVER";
export type ActivationPermission =
  "JOIN_COURSE" | "ACCESS_DISCORD" | "ASK_QUESTIONS" | "VIEW_ARCHIVE";

export interface ActivationBinding {
  kind: BindingKind;
  valueHash: Sha256Hash | null;
}

export interface PermissionProfile {
  role: ActivationRole;
  courseId: string;
  classCode: string | null;
  permissions: ActivationPermission[];
}

export interface ActivationRecord {
  schemaVersion: "1.0";
  activationCodeId: string;
  verifierHash: Sha256Hash;
  status: ActivationStatus;
  createdByUserId: string;
  redeemedByUserId: string | null;
  binding: ActivationBinding;
  permissionProfile: PermissionProfile;
  createdAt: string;
  expiresAt: string;
  redeemedAt: string | null;
  revokedAt: string | null;
  redemptionRequestHash: Sha256Hash | null;
}

export interface ActivationRepository {
  findById(activationCodeId: string): ActivationRecord | null;
  findByVerifierHash(verifierHash: Sha256Hash): ActivationRecord | null;
  insert(record: ActivationRecord): void;
  save(record: ActivationRecord): void;
}

export interface RandomBytesSource {
  bytes(length: number): Uint8Array;
}

export interface Sha256Hasher {
  hash(value: string): Sha256Hash;
}

export interface ActivationLock {
  runExclusive<T>(key: string, operation: () => T): T;
}

export interface ActivationClock {
  now(): string;
}

export interface ActivationAuditEvent {
  eventType:
    | "ACTIVATION_CODE_CREATED"
    | "ACTIVATION_CODE_REDEEMED"
    | "ACTIVATION_CODE_REVOKED";
  activationCodeId: string | null;
  outcome: string;
  occurredAt: string;
}

export interface ActivationAuditSink {
  record(event: ActivationAuditEvent): void;
}

export interface IssueActivationInput {
  createdByUserId: string;
  ttlMinutes: number;
  binding: { kind: "NONE" } | { kind: "EMAIL" | "DISCORD_USER"; value: string };
  permissionProfile: PermissionProfile;
}

export interface IssuedActivation {
  plaintextCode: string;
  record: ActivationRecord;
}

export interface RedeemActivationInput {
  plaintextCode: string;
  redeemedByUserId: string;
  bindingValue?: string;
  idempotencyKey: string;
}

export type RedemptionOutcome =
  | "REDEEMED"
  | "INVALID"
  | "NOT_FOUND"
  | "EXPIRED"
  | "REVOKED"
  | "USED"
  | "REPLAY"
  | "BINDING_MISMATCH";

export interface RedemptionResult {
  ok: boolean;
  outcome: RedemptionOutcome;
  activationCodeId: string | null;
  permissionProfile: PermissionProfile | null;
}
