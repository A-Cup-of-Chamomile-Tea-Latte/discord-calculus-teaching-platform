import { describe, expect, it, vi } from "vitest";

import {
  MailAppVerificationEmailProvider,
  type DeliveryReceiptStore,
  type DurableVerificationEmailDelivery,
} from "./mail-app-provider";

const DELIVERY: DurableVerificationEmailDelivery = {
  deliveryId: "email_delivery_12345678",
  challengeId: "email_verification_12345678",
  destination: "student@example.com",
  code: "123456",
  kind: "INSTITUTIONAL",
  expiresAt: "2099-08-27T12:00:00+08:00",
};

class MemoryReceipts implements DeliveryReceiptStore {
  readonly values = new Map<string, string>();

  get(deliveryId: string): string | null {
    return this.values.get(deliveryId) ?? null;
  }

  set(deliveryId: string, value: string): void {
    this.values.set(deliveryId, value);
  }
}

describe("standalone MailApp verification provider", () => {
  it("sends one plain-text message and makes accepted retries a no-op", () => {
    const receipts = new MemoryReceipts();
    const sendEmail = vi.fn();
    const provider = new MailAppVerificationEmailProvider(
      { getRemainingDailyQuota: () => 50, sendEmail },
      receipts,
      10,
      () => "2099-08-27 12:00",
    );

    expect(provider.sendDurable(DELIVERY)).toMatchObject({
      status: "PROVIDER_ACCEPTED",
      safeResultCode: "EMAIL_PROVIDER_ACCEPTED",
    });
    expect(provider.sendDurable(DELIVERY).status).toBe("NO_OP");
    expect(sendEmail).toHaveBeenCalledTimes(1);
    expect(sendEmail.mock.calls[0]?.[2]).toContain("123456");
    expect(sendEmail.mock.calls[0]?.[2]).not.toMatch(/<[^>]+>/);
  });

  it("preserves the configured quota reserve without attempting delivery", () => {
    const receipts = new MemoryReceipts();
    const sendEmail = vi.fn();
    const provider = new MailAppVerificationEmailProvider(
      { getRemainingDailyQuota: () => 10, sendEmail },
      receipts,
      10,
      () => "2099-08-27 12:00",
    );

    expect(() => provider.sendDurable(DELIVERY)).toThrow(
      "EMAIL_QUOTA_RESERVED",
    );
    expect(sendEmail).not.toHaveBeenCalled();
    expect(receipts.values.size).toBe(0);
  });

  it("fails closed after an ambiguous provider exception", () => {
    const receipts = new MemoryReceipts();
    const provider = new MailAppVerificationEmailProvider(
      {
        getRemainingDailyQuota: () => 50,
        sendEmail: () => {
          throw new Error("fixture provider failure");
        },
      },
      receipts,
      10,
      () => "2099-08-27 12:00",
    );

    expect(() => provider.sendDurable(DELIVERY)).toThrow(
      "EMAIL_DELIVERY_AMBIGUOUS",
    );
    expect(receipts.values.get(DELIVERY.deliveryId)).toBe("AMBIGUOUS");
    expect(() => provider.sendDurable(DELIVERY)).toThrow(
      "EMAIL_DELIVERY_AMBIGUOUS",
    );
  });

  it("rejects malformed destinations and expired codes before MailApp", () => {
    const sendEmail = vi.fn();
    const provider = new MailAppVerificationEmailProvider(
      { getRemainingDailyQuota: () => 50, sendEmail },
      new MemoryReceipts(),
      10,
      () => "2099-08-27 12:00",
    );

    expect(() =>
      provider.sendDurable({
        ...DELIVERY,
        destination: "a@example.com,b@example.com",
      }),
    ).toThrow("EMAIL_DELIVERY_INVALID");
    expect(() =>
      provider.sendDurable({ ...DELIVERY, expiresAt: "2020-01-01T00:00:00Z" }),
    ).toThrow("EMAIL_CODE_EXPIRED");
    expect(sendEmail).not.toHaveBeenCalled();
  });
});
