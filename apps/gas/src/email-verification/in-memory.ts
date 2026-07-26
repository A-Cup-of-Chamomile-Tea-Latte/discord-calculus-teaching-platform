import type {
  EmailVerificationAuditEvent,
  EmailVerificationAuditSink,
  EmailVerificationChallenge,
  EmailVerificationRepository,
  InstitutionalEmailPolicy,
  VerificationEmailDelivery,
  VerificationEmailProvider,
  VerificationLock,
  VerifiedEmailRecord,
} from "./contracts";

const cloneChallenge = (
  challenge: EmailVerificationChallenge,
): EmailVerificationChallenge => ({ ...challenge });

const cloneVerified = (record: VerifiedEmailRecord): VerifiedEmailRecord => ({
  ...record,
});

export class InMemoryEmailVerificationRepository implements EmailVerificationRepository {
  private readonly challenges = new Map<string, EmailVerificationChallenge>();
  private readonly verifiedEmails = new Map<string, VerifiedEmailRecord>();

  findChallenge(challengeId: string): EmailVerificationChallenge | null {
    const challenge = this.challenges.get(challengeId);
    return challenge ? cloneChallenge(challenge) : null;
  }

  findLatestChallenge(
    userId: string,
    email: string,
    kind: EmailVerificationChallenge["kind"],
  ): EmailVerificationChallenge | null {
    const match = [...this.challenges.values()]
      .filter(
        (challenge) =>
          challenge.userId === userId &&
          challenge.email === email &&
          challenge.kind === kind,
      )
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))[0];
    return match ? cloneChallenge(match) : null;
  }

  findVerifiedByEmail(email: string): VerifiedEmailRecord | null {
    const record = this.verifiedEmails.get(email);
    return record ? cloneVerified(record) : null;
  }

  insertChallenge(challenge: EmailVerificationChallenge): void {
    if (this.challenges.has(challenge.challengeId)) {
      throw new Error("EMAIL_CHALLENGE_ID_COLLISION");
    }
    this.challenges.set(challenge.challengeId, cloneChallenge(challenge));
  }

  saveChallenge(challenge: EmailVerificationChallenge): void {
    if (!this.challenges.has(challenge.challengeId)) {
      throw new Error("EMAIL_CHALLENGE_NOT_FOUND");
    }
    this.challenges.set(challenge.challengeId, cloneChallenge(challenge));
  }

  insertVerified(record: VerifiedEmailRecord): void {
    if (this.verifiedEmails.has(record.email)) {
      throw new Error("EMAIL_ALREADY_VERIFIED");
    }
    this.verifiedEmails.set(record.email, cloneVerified(record));
  }

  challengeSnapshot(): EmailVerificationChallenge[] {
    return [...this.challenges.values()].map(cloneChallenge);
  }

  verifiedSnapshot(): VerifiedEmailRecord[] {
    return [...this.verifiedEmails.values()].map(cloneVerified);
  }
}

export class MemoryVerificationEmailProvider implements VerificationEmailProvider {
  readonly deliveries: VerificationEmailDelivery[] = [];

  sendVerificationCode(delivery: VerificationEmailDelivery): void {
    this.deliveries.push({ ...delivery });
  }
}

export class MemoryEmailVerificationAuditSink implements EmailVerificationAuditSink {
  readonly events: EmailVerificationAuditEvent[] = [];

  record(event: EmailVerificationAuditEvent): void {
    this.events.push({ ...event });
  }
}

export class InMemoryVerificationLock implements VerificationLock {
  readonly keys: string[] = [];

  runExclusive<T>(key: string, operation: () => T): T {
    this.keys.push(key);
    return operation();
  }
}

export class DomainAllowlistInstitutionalEmailPolicy implements InstitutionalEmailPolicy {
  private readonly domains: Set<string>;

  constructor(domains: readonly string[]) {
    this.domains = new Set(domains.map((domain) => domain.toLowerCase()));
  }

  accepts(email: string): boolean {
    const domain = email.split("@")[1];
    return domain ? this.domains.has(domain.toLowerCase()) : false;
  }
}
