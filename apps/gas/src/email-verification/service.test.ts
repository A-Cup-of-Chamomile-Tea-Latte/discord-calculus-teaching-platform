import { createHash } from "node:crypto";

import { describe, expect, it } from "vitest";

import { SequenceRandomSource } from "../activation/in-memory";
import type { Sha256Hash, Sha256Hasher, VerificationClock } from "./contracts";
import {
  DomainAllowlistInstitutionalEmailPolicy,
  InMemoryEmailVerificationRepository,
  InMemoryVerificationLock,
  MemoryEmailVerificationAuditSink,
  MemoryVerificationEmailProvider,
} from "./in-memory";
import { EmailVerificationService } from "./service";

class NodeSha256Hasher implements Sha256Hasher {
  hash(value: string): Sha256Hash {
    return `sha256:${createHash("sha256").update(value).digest("hex")}`;
  }
}

class MutableClock implements VerificationClock {
  constructor(public current: string) {}

  now(): string {
    return this.current;
  }
}

function harness(
  policy: ConstructorParameters<
    typeof EmailVerificationService
  >[0]["policy"] = {},
) {
  const repository = new InMemoryEmailVerificationRepository();
  const emailProvider = new MemoryVerificationEmailProvider();
  const audit = new MemoryEmailVerificationAuditSink();
  const lock = new InMemoryVerificationLock();
  const clock = new MutableClock("2026-07-19T09:00:00.000Z");
  const service = new EmailVerificationService({
    repository,
    emailProvider,
    auditSink: audit,
    lock,
    clock,
    hasher: new NodeSha256Hasher(),
    randomSource: new SequenceRandomSource([...Array(256).keys()]),
    institutionalPolicy: new DomainAllowlistInstitutionalEmailPolicy([
      "institution.example",
    ]),
    policy,
  });
  return { service, repository, emailProvider, audit, lock, clock };
}

describe("provider-neutral email verification", () => {
  it("runs an institutional mock flow end to end without storing the code", () => {
    const { service, repository, emailProvider, audit } = harness();
    const started = service.start({
      userId: "usr_fixture_student",
      email: " Fixture.Student@Institution.Example ",
      kind: "INSTITUTIONAL",
      isPrimary: true,
    });
    expect(started).toMatchObject({ ok: true, outcome: "STARTED" });
    const delivery = emailProvider.deliveries[0]!;
    expect(delivery.code).toMatch(/^[0-9]{6}$/);
    const stored = repository.challengeSnapshot()[0]!;
    expect(stored.email).toBe("fixture.student@institution.example");
    expect(stored.codeHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    expect(stored.codeSalt).toMatch(/^[a-f0-9]{32}$/);
    expect(JSON.stringify(stored)).not.toContain(delivery.code);

    const verified = service.verify(started.challengeId!, delivery.code);
    expect(verified).toMatchObject({
      ok: true,
      outcome: "VERIFIED",
      verifiedEmail: {
        userId: "usr_fixture_student",
        kind: "INSTITUTIONAL",
        isPrimary: true,
      },
    });
    expect(repository.verifiedSnapshot()).toHaveLength(1);
    expect(service.verify(started.challengeId!, delivery.code).outcome).toBe(
      "ALREADY_VERIFIED",
    );
    expect(JSON.stringify(audit.events)).not.toContain(delivery.code);
  });

  it("requires a separate verification for an optional contact email", () => {
    const { service, emailProvider, repository } = harness();
    const institutional = service.start({
      userId: "usr_fixture_student",
      email: "student@institution.example",
      kind: "INSTITUTIONAL",
      isPrimary: false,
    });
    service.verify(
      institutional.challengeId!,
      emailProvider.deliveries[0]!.code,
    );

    const contact = service.start({
      userId: "usr_fixture_student",
      email: "student.contact@example.com",
      kind: "CONTACT",
      isPrimary: true,
    });
    expect(contact.outcome).toBe("STARTED");
    expect(repository.verifiedSnapshot()).toHaveLength(1);
    service.verify(contact.challengeId!, emailProvider.deliveries[1]!.code);
    expect(repository.verifiedSnapshot()).toMatchObject([
      { kind: "INSTITUTIONAL", isPrimary: false },
      { kind: "CONTACT", isPrimary: true },
    ]);
  });

  it("expires a code and refuses it afterward", () => {
    const { service, emailProvider, repository, clock } = harness();
    const started = service.start({
      userId: "usr_fixture_student",
      email: "student@institution.example",
      kind: "INSTITUTIONAL",
      isPrimary: true,
    });
    clock.current = "2026-07-19T09:10:00.000Z";
    expect(
      service.verify(started.challengeId!, emailProvider.deliveries[0]!.code)
        .outcome,
    ).toBe("EXPIRED");
    expect(repository.challengeSnapshot()[0]!.status).toBe("EXPIRED");
    expect(repository.verifiedSnapshot()).toHaveLength(0);
  });

  it("locks after the configured wrong-attempt limit", () => {
    const { service, emailProvider, repository, clock } = harness({
      maxAttempts: 3,
    });
    const input = {
      userId: "usr_fixture_student",
      email: "student@institution.example",
      kind: "INSTITUTIONAL" as const,
      isPrimary: true,
    };
    const started = service.start(input);
    expect(service.verify(started.challengeId!, "999999")).toMatchObject({
      outcome: "WRONG_CODE",
      attemptsRemaining: 2,
    });
    expect(service.verify(started.challengeId!, "999998")).toMatchObject({
      outcome: "WRONG_CODE",
      attemptsRemaining: 1,
    });
    expect(service.verify(started.challengeId!, "999997")).toMatchObject({
      outcome: "LOCKED",
      attemptsRemaining: 0,
    });
    expect(
      service.verify(started.challengeId!, emailProvider.deliveries[0]!.code)
        .outcome,
    ).toBe("LOCKED");
    expect(repository.verifiedSnapshot()).toHaveLength(0);
    expect(service.start(input).outcome).toBe("ATTEMPT_LOCKED");
    expect(emailProvider.deliveries).toHaveLength(1);

    clock.current = "2026-07-19T09:10:00.000Z";
    expect(service.start(input).outcome).toBe("STARTED");
    expect(emailProvider.deliveries).toHaveLength(2);
  });

  it("enforces resend cooldown and invalidates the previous code", () => {
    const { service, emailProvider, clock } = harness();
    const input = {
      userId: "usr_fixture_student",
      email: "student@institution.example",
      kind: "INSTITUTIONAL" as const,
      isPrimary: true,
    };
    const started = service.start(input);
    const firstCode = emailProvider.deliveries[0]!.code;
    expect(service.start(input).outcome).toBe("COOLDOWN");
    expect(emailProvider.deliveries).toHaveLength(1);

    clock.current = "2026-07-19T09:01:00.000Z";
    expect(service.start(input).outcome).toBe("RESENT");
    expect(emailProvider.deliveries).toHaveLength(2);
    const secondCode = emailProvider.deliveries[1]!.code;
    expect(secondCode).not.toBe(firstCode);
    expect(service.verify(started.challengeId!, firstCode).outcome).toBe(
      "WRONG_CODE",
    );
    expect(service.verify(started.challengeId!, secondCode).outcome).toBe(
      "VERIFIED",
    );
  });

  it("stops resends at the per-challenge send limit", () => {
    const { service, emailProvider, clock } = harness({
      maxSendsPerChallenge: 2,
    });
    const input = {
      userId: "usr_fixture_student",
      email: "student@institution.example",
      kind: "INSTITUTIONAL" as const,
      isPrimary: true,
    };
    service.start(input);
    clock.current = "2026-07-19T09:01:00.000Z";
    service.start(input);
    clock.current = "2026-07-19T09:02:00.000Z";
    expect(service.start(input).outcome).toBe("SEND_LIMIT");
    expect(emailProvider.deliveries).toHaveLength(2);
  });

  it("rejects a contact-domain address as institutional", () => {
    const { service, emailProvider } = harness();
    expect(() =>
      service.start({
        userId: "usr_fixture_student",
        email: "student@example.com",
        kind: "INSTITUTIONAL",
        isPrimary: true,
      }),
    ).toThrow("EMAIL_NOT_INSTITUTIONAL");
    expect(emailProvider.deliveries).toHaveLength(0);
  });

  it("keeps audit events free of email addresses and codes", () => {
    const { service, emailProvider, audit } = harness();
    const started = service.start({
      userId: "usr_fixture_student",
      email: "private.fixture@institution.example",
      kind: "INSTITUTIONAL",
      isPrimary: true,
    });
    service.verify(started.challengeId!, "999999");
    const serialized = JSON.stringify(audit.events);
    expect(serialized).not.toContain("private.fixture@institution.example");
    expect(serialized).not.toContain(emailProvider.deliveries[0]!.code);
  });
});
