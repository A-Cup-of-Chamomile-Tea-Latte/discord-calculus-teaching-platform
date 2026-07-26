import { createHash } from "node:crypto";

import { describe, expect, it } from "vitest";

import type {
  ActivationClock,
  ActivationRecord,
  PermissionProfile,
  Sha256Hash,
  Sha256Hasher,
} from "./contracts";
import {
  InMemoryActivationLock,
  InMemoryActivationRepository,
  MemoryActivationAuditSink,
  SequenceRandomSource,
} from "./in-memory";
import { WebCryptoRandomSource } from "./runtime-providers";
import { ActivationService, normalizeActivationCode } from "./service";

class NodeSha256Hasher implements Sha256Hasher {
  hash(value: string): Sha256Hash {
    return `sha256:${createHash("sha256").update(value).digest("hex")}`;
  }
}

class MutableClock implements ActivationClock {
  constructor(public current: string) {}

  now(): string {
    return this.current;
  }
}

const permissionProfile: PermissionProfile = {
  role: "STUDENT",
  courseId: "calculus_1151",
  classCode: "01",
  permissions: ["JOIN_COURSE", "ACCESS_DISCORD", "ASK_QUESTIONS"],
};

function harness(
  binding: Parameters<ActivationService["issue"]>[0]["binding"] = {
    kind: "NONE",
  },
) {
  const repository = new InMemoryActivationRepository();
  const audit = new MemoryActivationAuditSink();
  const lock = new InMemoryActivationLock();
  const clock = new MutableClock("2026-07-19T08:00:00.000Z");
  const service = new ActivationService({
    repository,
    randomSource: new SequenceRandomSource([...Array(16).keys()]),
    hasher: new NodeSha256Hasher(),
    lock,
    auditSink: audit,
    clock,
  });
  const issued = service.issue({
    createdByUserId: "usr_staff_example",
    ttlMinutes: 30,
    binding,
    permissionProfile,
  });
  return { service, repository, audit, lock, clock, issued };
}

describe("single-use activation code domain logic", () => {
  it("issues a human-enterable code and stores only fingerprints", () => {
    const { issued, repository, audit } = harness({
      kind: "EMAIL",
      value: "Fixture.Student@Example.com",
    });
    expect(issued.plaintextCode).toMatch(
      /^CALC-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{4}(?:-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{4}){3}$/,
    );
    expect(
      normalizeActivationCode(`  ${issued.plaintextCode.toLowerCase()} `),
    ).toHaveLength(20);
    const stored = repository.snapshot()[0]!;
    expect(stored.verifierHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    expect(stored.binding).toMatchObject({ kind: "EMAIL" });
    expect(stored.binding.valueHash).toMatch(/^sha256:[a-f0-9]{64}$/);
    expect(JSON.stringify(stored)).not.toContain(issued.plaintextCode);
    expect(JSON.stringify(stored)).not.toContain("fixture.student@example.com");
    expect(stored.permissionProfile).toEqual(permissionProfile);
    expect(JSON.stringify(audit.events)).not.toContain(issued.plaintextCode);
  });

  it("redeems exactly once and rejects replay/different second attempts", () => {
    const { service, repository, lock, issued } = harness();
    const first = service.redeem({
      plaintextCode: issued.plaintextCode,
      redeemedByUserId: "usr_fixture_student",
      idempotencyKey: "request-0001",
    });
    expect(first).toMatchObject({
      ok: true,
      outcome: "REDEEMED",
      permissionProfile,
    });
    expect(repository.snapshot()[0]).toMatchObject({
      status: "USED",
      redeemedByUserId: "usr_fixture_student",
      redeemedAt: "2026-07-19T08:00:00.000Z",
      redemptionRequestHash: expect.stringMatching(/^sha256:/),
    });
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        idempotencyKey: "request-0001",
      }).outcome,
    ).toBe("REPLAY");
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "usr_other_student",
        idempotencyKey: "request-0002",
      }).outcome,
    ).toBe("USED");
    expect(lock.keys).toHaveLength(3);
  });

  it("fails expired and revoked codes", () => {
    const expired = harness();
    expired.clock.current = "2026-07-19T08:31:00.000Z";
    expect(
      expired.service.redeem({
        plaintextCode: expired.issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        idempotencyKey: "request-expired",
      }).outcome,
    ).toBe("EXPIRED");
    expect(expired.repository.snapshot()[0]?.status).toBe("EXPIRED");

    const revoked = harness();
    expect(revoked.service.revoke(revoked.issued.plaintextCode).outcome).toBe(
      "REVOKED",
    );
    expect(
      revoked.service.redeem({
        plaintextCode: revoked.issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        idempotencyKey: "request-revoked",
      }).outcome,
    ).toBe("REVOKED");
  });

  it("fails a wrong email binding and accepts the normalized correct binding", () => {
    const { service, issued } = harness({
      kind: "EMAIL",
      value: "fixture.student@example.com",
    });
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        bindingValue: "wrong@example.com",
        idempotencyKey: "request-wrong-binding",
      }).outcome,
    ).toBe("BINDING_MISMATCH");
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        bindingValue: " FIXTURE.STUDENT@EXAMPLE.COM ",
        idempotencyKey: "request-right-binding",
      }).outcome,
    ).toBe("REDEEMED");
  });

  it("fails a wrong Discord user binding", () => {
    const { service, issued } = harness({
      kind: "DISCORD_USER",
      value: "123456789012345678",
    });
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        bindingValue: "223456789012345678",
        idempotencyKey: "request-discord-binding",
      }).outcome,
    ).toBe("BINDING_MISMATCH");
  });

  it("keeps deterministic randomness explicit and repeatable for fixtures", () => {
    const first = harness().issued.plaintextCode;
    const second = harness().issued.plaintextCode;
    expect(first).toBe(second);
    expect(first).toBe("CALC-ABCD-EFGH-JKLM-NPQR");
  });

  it("uses Web Crypto when available for runtime random bytes", () => {
    const bytes = new WebCryptoRandomSource().bytes(32);
    expect(bytes).toHaveLength(32);
    expect(new Set(bytes).size).toBeGreaterThan(1);
  });

  it("enforces runtime actor, role, permission, and idempotency allowlists", () => {
    const invalidRole = {
      ...permissionProfile,
      role: "ADMIN",
    } as unknown as PermissionProfile;
    expect(() =>
      new ActivationService({
        repository: new InMemoryActivationRepository(),
        randomSource: new SequenceRandomSource([...Array(16).keys()]),
        hasher: new NodeSha256Hasher(),
        lock: new InMemoryActivationLock(),
        auditSink: new MemoryActivationAuditSink(),
        clock: new MutableClock("2026-07-19T08:00:00.000Z"),
      }).issue({
        createdByUserId: "usr_staff_example",
        ttlMinutes: 30,
        binding: { kind: "NONE" },
        permissionProfile: invalidRole,
      }),
    ).toThrow("INVALID_PERMISSION_ROLE");

    const { service, issued } = harness();
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "invalid user",
        idempotencyKey: "request-valid",
      }).outcome,
    ).toBe("INVALID");
    expect(
      service.redeem({
        plaintextCode: issued.plaintextCode,
        redeemedByUserId: "usr_fixture_student",
        idempotencyKey: "contains spaces",
      }).outcome,
    ).toBe("INVALID");
  });

  it("audits lifecycle outcomes without plaintext or binding values", () => {
    const { service, issued, audit } = harness({
      kind: "EMAIL",
      value: "fixture.student@example.com",
    });
    service.redeem({
      plaintextCode: issued.plaintextCode,
      redeemedByUserId: "usr_fixture_student",
      bindingValue: "wrong@example.com",
      idempotencyKey: "request-audit",
    });
    const serialized = JSON.stringify(audit.events);
    expect(serialized).not.toContain(issued.plaintextCode);
    expect(serialized).not.toContain("fixture.student@example.com");
    expect(serialized).not.toContain("request-audit");
  });

  it("fixture repository records never gain a plaintextCode field", () => {
    const { repository } = harness();
    expect(
      Object.keys(repository.snapshot()[0] as ActivationRecord),
    ).not.toContain("plaintextCode");
  });
});
