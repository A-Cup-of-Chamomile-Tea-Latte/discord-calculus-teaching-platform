import type {
  ActivationAuditSink,
  ActivationBinding,
  ActivationClock,
  ActivationLock,
  ActivationRecord,
  ActivationRepository,
  IssuedActivation,
  IssueActivationInput,
  PermissionProfile,
  RandomBytesSource,
  RedeemActivationInput,
  RedemptionResult,
  Sha256Hash,
  Sha256Hasher,
} from "./contracts";

const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const compactPattern = /^CALC[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{16}$/;
const recordIdPattern = /^[a-z][a-z0-9_]{2,63}$/;
const idempotencyKeyPattern = /^[A-Za-z0-9._:-]{8,128}$/;
const roles = new Set(["STUDENT", "TA", "INSTRUCTOR", "OBSERVER"]);
const permissions = new Set([
  "JOIN_COURSE",
  "ACCESS_DISCORD",
  "ASK_QUESTIONS",
  "VIEW_ARCHIVE",
]);

export interface ActivationServiceDependencies {
  repository: ActivationRepository;
  randomSource: RandomBytesSource;
  hasher: Sha256Hasher;
  lock: ActivationLock;
  auditSink: ActivationAuditSink;
  clock: ActivationClock;
}

function cloneProfile(profile: PermissionProfile): PermissionProfile {
  return { ...profile, permissions: [...profile.permissions] };
}

function constantTimeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function normalizeBindingValue(
  kind: "EMAIL" | "DISCORD_USER",
  value: string,
): string {
  const normalized =
    kind === "EMAIL" ? value.trim().toLowerCase() : value.trim();
  if (kind === "EMAIL" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) {
    throw new Error("INVALID_EMAIL_BINDING");
  }
  if (kind === "DISCORD_USER" && !/^[0-9]{17,20}$/.test(normalized)) {
    throw new Error("INVALID_DISCORD_BINDING");
  }
  return normalized;
}

function validatePermissionProfile(profile: PermissionProfile): void {
  if (!roles.has(profile.role)) {
    throw new Error("INVALID_PERMISSION_ROLE");
  }
  if (!/^[a-z][a-z0-9_-]{2,63}$/.test(profile.courseId)) {
    throw new Error("INVALID_PERMISSION_COURSE_ID");
  }
  if (profile.classCode !== null && !/^[0-9]{2}$/.test(profile.classCode)) {
    throw new Error("INVALID_PERMISSION_CLASS_CODE");
  }
  if (
    profile.permissions.length === 0 ||
    new Set(profile.permissions).size !== profile.permissions.length ||
    profile.permissions.some((permission) => !permissions.has(permission))
  ) {
    throw new Error("INVALID_PERMISSION_SET");
  }
}

export function normalizeActivationCode(value: string): string | null {
  const compact = value
    .trim()
    .toUpperCase()
    .replace(/[\s-]+/g, "");
  return compactPattern.test(compact) ? compact : null;
}

function displayCode(compact: string): string {
  return [compact.slice(0, 4), ...compact.slice(4).match(/.{4}/g)!].join("-");
}

export class ActivationService {
  constructor(private readonly dependencies: ActivationServiceDependencies) {}

  private hashBinding(
    binding: IssueActivationInput["binding"],
  ): ActivationBinding {
    if (binding.kind === "NONE") return { kind: "NONE", valueHash: null };
    const normalized = normalizeBindingValue(binding.kind, binding.value);
    return {
      kind: binding.kind,
      valueHash: this.dependencies.hasher.hash(
        `binding:${binding.kind}:${normalized}`,
      ),
    };
  }

  issue(input: IssueActivationInput): IssuedActivation {
    if (!recordIdPattern.test(input.createdByUserId)) {
      throw new Error("INVALID_CREATED_BY_USER_ID");
    }
    if (
      !Number.isInteger(input.ttlMinutes) ||
      input.ttlMinutes < 5 ||
      input.ttlMinutes > 10080
    ) {
      throw new Error("INVALID_ACTIVATION_TTL");
    }
    validatePermissionProfile(input.permissionProfile);
    const createdAt = this.dependencies.clock.now();
    if (Number.isNaN(new Date(createdAt).getTime())) {
      throw new Error("INVALID_CLOCK_OUTPUT");
    }
    const expiresAt = new Date(
      new Date(createdAt).getTime() + input.ttlMinutes * 60_000,
    ).toISOString();
    const random = this.dependencies.randomSource.bytes(16);
    if (random.length !== 16) throw new Error("INVALID_RANDOM_SOURCE_OUTPUT");
    const symbols = [...random].map((byte) => alphabet[byte & 31]).join("");
    const compact = `CALC${symbols}`;
    const verifierHash = this.dependencies.hasher.hash(compact);
    const activationCodeId = `activation_${verifierHash.slice(7, 23)}`;
    const record: ActivationRecord = {
      schemaVersion: "1.0",
      activationCodeId,
      verifierHash,
      status: "UNUSED",
      createdByUserId: input.createdByUserId,
      redeemedByUserId: null,
      binding: this.hashBinding(input.binding),
      permissionProfile: cloneProfile(input.permissionProfile),
      createdAt,
      expiresAt,
      redeemedAt: null,
      revokedAt: null,
      redemptionRequestHash: null,
    };
    this.dependencies.repository.insert(record);
    this.dependencies.auditSink.record({
      eventType: "ACTIVATION_CODE_CREATED",
      activationCodeId,
      outcome: "CREATED",
      occurredAt: createdAt,
    });
    return {
      plaintextCode: displayCode(compact),
      record: {
        ...record,
        binding: { ...record.binding },
        permissionProfile: cloneProfile(record.permissionProfile),
      },
    };
  }

  redeem(input: RedeemActivationInput): RedemptionResult {
    const compact = normalizeActivationCode(input.plaintextCode);
    if (
      !compact ||
      !recordIdPattern.test(input.redeemedByUserId) ||
      !idempotencyKeyPattern.test(input.idempotencyKey)
    ) {
      return this.result("INVALID", null);
    }
    const verifierHash = this.dependencies.hasher.hash(compact);
    return this.dependencies.lock.runExclusive(verifierHash, () => {
      const record =
        this.dependencies.repository.findByVerifierHash(verifierHash);
      if (!record) return this.result("NOT_FOUND", null);
      const requestHash = this.dependencies.hasher.hash(
        `redemption:${input.idempotencyKey}`,
      );
      if (record.status === "USED") {
        const outcome =
          record.redemptionRequestHash &&
          constantTimeEqual(record.redemptionRequestHash, requestHash)
            ? "REPLAY"
            : "USED";
        return this.result(outcome, record);
      }
      if (record.status === "REVOKED") return this.result("REVOKED", record);

      const now = this.dependencies.clock.now();
      if (
        record.status === "EXPIRED" ||
        new Date(now) >= new Date(record.expiresAt)
      ) {
        if (record.status !== "EXPIRED") {
          record.status = "EXPIRED";
          this.dependencies.repository.save(record);
        }
        return this.result("EXPIRED", record);
      }

      if (record.binding.kind !== "NONE") {
        if (!input.bindingValue || !record.binding.valueHash) {
          return this.result("BINDING_MISMATCH", record);
        }
        let normalized: string;
        try {
          normalized = normalizeBindingValue(
            record.binding.kind,
            input.bindingValue,
          );
        } catch {
          return this.result("BINDING_MISMATCH", record);
        }
        const candidate = this.dependencies.hasher.hash(
          `binding:${record.binding.kind}:${normalized}`,
        );
        if (!constantTimeEqual(record.binding.valueHash, candidate)) {
          return this.result("BINDING_MISMATCH", record);
        }
      }

      record.status = "USED";
      record.redeemedByUserId = input.redeemedByUserId;
      record.redeemedAt = now;
      record.redemptionRequestHash = requestHash;
      this.dependencies.repository.save(record);
      return this.result("REDEEMED", record);
    });
  }

  revoke(plaintextCode: string): RedemptionResult {
    const compact = normalizeActivationCode(plaintextCode);
    if (!compact)
      return this.result("INVALID", null, "ACTIVATION_CODE_REVOKED");
    const verifierHash = this.dependencies.hasher.hash(compact);
    return this.dependencies.lock.runExclusive(verifierHash, () => {
      const record =
        this.dependencies.repository.findByVerifierHash(verifierHash);
      if (!record)
        return this.result("NOT_FOUND", null, "ACTIVATION_CODE_REVOKED");
      if (record.status === "USED")
        return this.result("USED", record, "ACTIVATION_CODE_REVOKED");
      if (record.status === "REVOKED")
        return this.result("REVOKED", record, "ACTIVATION_CODE_REVOKED");
      record.status = "REVOKED";
      record.revokedAt = this.dependencies.clock.now();
      this.dependencies.repository.save(record);
      return this.result("REVOKED", record, "ACTIVATION_CODE_REVOKED");
    });
  }

  private result(
    outcome: RedemptionResult["outcome"],
    record: ActivationRecord | null,
    eventType:
      | "ACTIVATION_CODE_REDEEMED"
      | "ACTIVATION_CODE_REVOKED" = "ACTIVATION_CODE_REDEEMED",
  ): RedemptionResult {
    const ok = outcome === "REDEEMED";
    this.dependencies.auditSink.record({
      eventType,
      activationCodeId: record?.activationCodeId ?? null,
      outcome,
      occurredAt: this.dependencies.clock.now(),
    });
    return {
      ok,
      outcome,
      activationCodeId: record?.activationCodeId ?? null,
      permissionProfile:
        ok && record ? cloneProfile(record.permissionProfile) : null,
    };
  }
}
