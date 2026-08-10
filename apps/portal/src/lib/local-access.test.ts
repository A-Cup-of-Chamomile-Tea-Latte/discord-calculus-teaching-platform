import { describe, expect, it } from "vitest";

import {
  createEmptyAccessStore,
  createLocalAccount,
  hashAccountId,
  normalizeAccountId,
  passwordPolicyError,
  replaceLocalPassword,
  roleAllows,
  validSession,
  verifyLocalAccount,
} from "./local-access";

describe("local access", () => {
  it("normalizes and hashes the account identifier", async () => {
    const store = createEmptyAccessStore();
    expect(normalizeAccountId("  B12345678 ")).toBe("b12345678");
    await expect(
      hashAccountId("B12345678", store.accountLookupSalt),
    ).resolves.toBe(await hashAccountId("b12345678", store.accountLookupSalt));
  });

  it("stores only salted verifiers and validates a password", async () => {
    const store = createEmptyAccessStore();
    const account = await createLocalAccount(
      "staff_fixture",
      "staff",
      store.accountLookupSalt,
      { iterations: 1_000 },
    );
    expect(JSON.stringify(account)).not.toContain("staff_fixture");
    await expect(verifyLocalAccount(account, "staff_fixture")).resolves.toBe(
      true,
    );
    await expect(verifyLocalAccount(account, "wrong-password")).resolves.toBe(
      false,
    );
  });

  it("replaces the one-time password and clears the change flag", async () => {
    const store = createEmptyAccessStore();
    const account = await createLocalAccount(
      "admin_fixture",
      "admin",
      store.accountLookupSalt,
      { iterations: 1_000 },
    );
    const changed = await replaceLocalPassword(
      account,
      "new-local-passphrase",
      1_000,
    );
    expect(changed.mustChangePassword).toBe(false);
    await expect(
      verifyLocalAccount(changed, "new-local-passphrase"),
    ).resolves.toBe(true);
  });

  it("checks password, session and role rules", () => {
    expect(passwordPolicyError("short", "staff_fixture")).toBeTruthy();
    expect(passwordPolicyError("staff_fixture", "staff_fixture")).toBeTruthy();
    expect(
      passwordPolicyError("a sufficiently long phrase", "staff_fixture"),
    ).toBeNull();
    expect(
      validSession({ accountHash: "hash", role: "staff", expiresAt: 20 }, 10),
    ).toBe(true);
    expect(roleAllows("staff", "admin")).toBe(false);
    expect(roleAllows("admin", "staff")).toBe(true);
  });
});
