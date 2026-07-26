import type {
  EmailVerificationChallenge,
  EmailVerificationRepository,
  InstitutionalEmailPolicy,
  RandomBytesSource,
  Sha256Hasher,
  StartVerificationInput,
  StartVerificationResult,
  VerificationClock,
  VerificationEmailProvider,
  VerificationLock,
  VerifyCodeOutcome,
  VerifyCodeResult,
  VerifiedEmailRecord,
  EmailVerificationAuditSink,
} from "./contracts";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const recordIdPattern = /^[a-z][a-z0-9_]{2,63}$/;
const codePattern = /^[0-9]{6}$/;
const oneMillion = 1_000_000;
const unbiasedLimit = 16_000_000;

export interface EmailVerificationPolicy {
  codeTtlMinutes: number;
  maxAttempts: number;
  resendCooldownSeconds: number;
  maxSendsPerChallenge: number;
}

export interface EmailVerificationDependencies {
  repository: EmailVerificationRepository;
  emailProvider: VerificationEmailProvider;
  institutionalPolicy: InstitutionalEmailPolicy;
  randomSource: RandomBytesSource;
  hasher: Sha256Hasher;
  clock: VerificationClock;
  lock: VerificationLock;
  auditSink: EmailVerificationAuditSink;
  policy?: Partial<EmailVerificationPolicy>;
}

const defaultPolicy: EmailVerificationPolicy = {
  codeTtlMinutes: 10,
  maxAttempts: 5,
  resendCooldownSeconds: 60,
  maxSendsPerChallenge: 3,
};

function normalizeEmail(value: string): string {
  const normalized = value.trim().toLowerCase();
  if (normalized.length > 254 || !emailPattern.test(normalized)) {
    throw new Error("INVALID_EMAIL");
  }
  return normalized;
}

function constantTimeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function bytesToHex(bytes: Uint8Array): string {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export class EmailVerificationService {
  private readonly policy: EmailVerificationPolicy;

  constructor(private readonly dependencies: EmailVerificationDependencies) {
    this.policy = { ...defaultPolicy, ...dependencies.policy };
    if (
      !Number.isInteger(this.policy.codeTtlMinutes) ||
      this.policy.codeTtlMinutes < 1 ||
      this.policy.codeTtlMinutes > 30 ||
      !Number.isInteger(this.policy.maxAttempts) ||
      this.policy.maxAttempts < 1 ||
      this.policy.maxAttempts > 10 ||
      !Number.isInteger(this.policy.resendCooldownSeconds) ||
      this.policy.resendCooldownSeconds < 30 ||
      this.policy.resendCooldownSeconds > 600 ||
      !Number.isInteger(this.policy.maxSendsPerChallenge) ||
      this.policy.maxSendsPerChallenge < 1 ||
      this.policy.maxSendsPerChallenge > 5
    ) {
      throw new Error("INVALID_EMAIL_VERIFICATION_POLICY");
    }
  }

  start(input: StartVerificationInput): StartVerificationResult {
    if (!recordIdPattern.test(input.userId)) {
      throw new Error("INVALID_USER_ID");
    }
    if (
      (input.kind !== "INSTITUTIONAL" && input.kind !== "CONTACT") ||
      typeof input.isPrimary !== "boolean"
    ) {
      throw new Error("INVALID_EMAIL_KIND_OR_PRIMARY_FLAG");
    }
    const email = normalizeEmail(input.email);
    if (
      input.kind === "INSTITUTIONAL" &&
      !this.dependencies.institutionalPolicy.accepts(email)
    ) {
      throw new Error("EMAIL_NOT_INSTITUTIONAL");
    }

    return this.dependencies.lock.runExclusive(
      `email-start:${input.userId}:${email}:${input.kind}`,
      () => {
        const verified =
          this.dependencies.repository.findVerifiedByEmail(email);
        if (verified) {
          this.audit(
            "EMAIL_VERIFICATION_STARTED",
            null,
            "ALREADY_VERIFIED",
            this.now(),
          );
          return {
            ok: false,
            outcome: "ALREADY_VERIFIED",
            challengeId: null,
            expiresAt: null,
            resendAvailableAt: null,
          };
        }

        const now = this.now();
        const latest = this.dependencies.repository.findLatestChallenge(
          input.userId,
          email,
          input.kind,
        );
        if (
          latest &&
          (latest.status === "PENDING" || latest.status === "LOCKED") &&
          new Date(now) >= new Date(latest.expiresAt)
        ) {
          latest.status = "EXPIRED";
          latest.updatedAt = now;
          this.dependencies.repository.saveChallenge(latest);
        }
        if (latest?.status === "LOCKED") {
          this.audit(
            "EMAIL_VERIFICATION_RESENT",
            latest.challengeId,
            "ATTEMPT_LOCKED",
            now,
          );
          return this.startResult("ATTEMPT_LOCKED", latest);
        }
        if (latest?.status === "PENDING") {
          if (new Date(now) < new Date(latest.resendAvailableAt)) {
            this.audit(
              "EMAIL_VERIFICATION_RESENT",
              latest.challengeId,
              "COOLDOWN",
              now,
            );
            return this.startResult("COOLDOWN", latest);
          }
          if (latest.sendCount >= this.policy.maxSendsPerChallenge) {
            this.audit(
              "EMAIL_VERIFICATION_RESENT",
              latest.challengeId,
              "SEND_LIMIT",
              now,
            );
            return this.startResult("SEND_LIMIT", latest);
          }
          const issued = this.issueCode();
          Object.assign(latest, {
            codeSalt: issued.salt,
            codeHash: issued.hash,
            attemptsRemaining: this.policy.maxAttempts,
            sendCount: latest.sendCount + 1,
            updatedAt: now,
            expiresAt: this.offset(now, this.policy.codeTtlMinutes * 60),
            resendAvailableAt: this.offset(
              now,
              this.policy.resendCooldownSeconds,
            ),
          });
          this.dependencies.repository.saveChallenge(latest);
          this.dependencies.emailProvider.sendVerificationCode({
            challengeId: latest.challengeId,
            destination: latest.email,
            code: issued.code,
            kind: latest.kind,
            expiresAt: latest.expiresAt,
          });
          this.audit(
            "EMAIL_VERIFICATION_RESENT",
            latest.challengeId,
            "RESENT",
            now,
          );
          return this.startResult("RESENT", latest);
        }

        const issued = this.issueCode();
        const challengeId = `email_verification_${issued.hash.slice(7, 23)}`;
        const challenge: EmailVerificationChallenge = {
          challengeId,
          userId: input.userId,
          email,
          kind: input.kind,
          isPrimary: input.isPrimary,
          status: "PENDING",
          codeSalt: issued.salt,
          codeHash: issued.hash,
          attemptsRemaining: this.policy.maxAttempts,
          sendCount: 1,
          createdAt: now,
          updatedAt: now,
          expiresAt: this.offset(now, this.policy.codeTtlMinutes * 60),
          resendAvailableAt: this.offset(
            now,
            this.policy.resendCooldownSeconds,
          ),
          verifiedAt: null,
        };
        this.dependencies.repository.insertChallenge(challenge);
        this.dependencies.emailProvider.sendVerificationCode({
          challengeId,
          destination: email,
          code: issued.code,
          kind: input.kind,
          expiresAt: challenge.expiresAt,
        });
        this.audit("EMAIL_VERIFICATION_STARTED", challengeId, "STARTED", now);
        return this.startResult("STARTED", challenge);
      },
    );
  }

  verify(challengeId: string, code: string): VerifyCodeResult {
    if (!recordIdPattern.test(challengeId) || !codePattern.test(code)) {
      return this.verifyResult("INVALID", null, null);
    }
    return this.dependencies.lock.runExclusive(
      `email-verify:${challengeId}`,
      () => {
        const challenge =
          this.dependencies.repository.findChallenge(challengeId);
        if (!challenge) return this.verifyResult("NOT_FOUND", null, null);
        if (challenge.status === "VERIFIED") {
          return this.verifyResult(
            "ALREADY_VERIFIED",
            challenge.attemptsRemaining,
            null,
            challengeId,
          );
        }
        if (challenge.status === "LOCKED") {
          return this.verifyResult("LOCKED", 0, null, challengeId);
        }
        const now = this.now();
        if (
          challenge.status === "EXPIRED" ||
          new Date(now) >= new Date(challenge.expiresAt)
        ) {
          challenge.status = "EXPIRED";
          challenge.updatedAt = now;
          this.dependencies.repository.saveChallenge(challenge);
          return this.verifyResult(
            "EXPIRED",
            challenge.attemptsRemaining,
            null,
            challengeId,
          );
        }

        const candidate = this.dependencies.hasher.hash(
          `email-verification:v1:${challenge.codeSalt}:${code}`,
        );
        if (!constantTimeEqual(challenge.codeHash, candidate)) {
          challenge.attemptsRemaining -= 1;
          challenge.updatedAt = now;
          if (challenge.attemptsRemaining === 0) challenge.status = "LOCKED";
          this.dependencies.repository.saveChallenge(challenge);
          return this.verifyResult(
            challenge.status === "LOCKED" ? "LOCKED" : "WRONG_CODE",
            challenge.attemptsRemaining,
            null,
            challengeId,
          );
        }

        challenge.status = "VERIFIED";
        challenge.verifiedAt = now;
        challenge.updatedAt = now;
        const record: VerifiedEmailRecord = {
          schemaVersion: "1.0",
          verifiedEmailId: `email_${challenge.challengeId.slice("email_verification_".length)}`,
          userId: challenge.userId,
          email: challenge.email,
          kind: challenge.kind,
          verifiedAt: now,
          isPrimary: challenge.isPrimary,
          createdAt: challenge.createdAt,
        };
        this.dependencies.repository.saveChallenge(challenge);
        this.dependencies.repository.insertVerified(record);
        return this.verifyResult(
          "VERIFIED",
          challenge.attemptsRemaining,
          record,
          challengeId,
        );
      },
    );
  }

  private issueCode(): {
    code: string;
    salt: string;
    hash: `sha256:${string}`;
  } {
    let value: number | null = null;
    for (let attempt = 0; attempt < 32; attempt += 1) {
      const bytes = this.dependencies.randomSource.bytes(3);
      if (bytes.length !== 3) throw new Error("INVALID_RANDOM_SOURCE_OUTPUT");
      const candidate = (bytes[0]! << 16) | (bytes[1]! << 8) | bytes[2]!;
      if (candidate < unbiasedLimit) {
        value = candidate % oneMillion;
        break;
      }
    }
    if (value === null) throw new Error("RANDOM_REJECTION_LIMIT");
    const code = value.toString().padStart(6, "0");
    const saltBytes = this.dependencies.randomSource.bytes(16);
    if (saltBytes.length !== 16)
      throw new Error("INVALID_RANDOM_SOURCE_OUTPUT");
    const salt = bytesToHex(saltBytes);
    return {
      code,
      salt,
      hash: this.dependencies.hasher.hash(
        `email-verification:v1:${salt}:${code}`,
      ),
    };
  }

  private now(): string {
    const now = this.dependencies.clock.now();
    if (Number.isNaN(new Date(now).getTime()))
      throw new Error("INVALID_CLOCK_OUTPUT");
    return now;
  }

  private offset(now: string, seconds: number): string {
    return new Date(new Date(now).getTime() + seconds * 1000).toISOString();
  }

  private startResult(
    outcome: StartVerificationResult["outcome"],
    challenge: EmailVerificationChallenge,
  ): StartVerificationResult {
    return {
      ok: outcome === "STARTED" || outcome === "RESENT",
      outcome,
      challengeId: challenge.challengeId,
      expiresAt: challenge.expiresAt,
      resendAvailableAt: challenge.resendAvailableAt,
    };
  }

  private verifyResult(
    outcome: VerifyCodeOutcome,
    attemptsRemaining: number | null,
    verifiedEmail: VerifiedEmailRecord | null,
    challengeId: string | null = null,
  ): VerifyCodeResult {
    this.audit(
      "EMAIL_VERIFICATION_ATTEMPTED",
      challengeId,
      outcome,
      this.now(),
    );
    return {
      ok: outcome === "VERIFIED",
      outcome,
      attemptsRemaining,
      verifiedEmail: verifiedEmail ? { ...verifiedEmail } : null,
    };
  }

  private audit(
    eventType:
      | "EMAIL_VERIFICATION_STARTED"
      | "EMAIL_VERIFICATION_RESENT"
      | "EMAIL_VERIFICATION_ATTEMPTED",
    challengeId: string | null,
    outcome: string,
    occurredAt: string,
  ): void {
    this.dependencies.auditSink.record({
      eventType,
      challengeId,
      outcome,
      occurredAt,
    });
  }
}
