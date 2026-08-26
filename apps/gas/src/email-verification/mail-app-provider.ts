import type { VerificationEmailDelivery } from "./contracts";

export interface MailAppPort {
  getRemainingDailyQuota(): number;
  sendEmail(recipient: string, subject: string, body: string): void;
}

export interface DeliveryReceiptStore {
  get(deliveryId: string): string | null;
  set(deliveryId: string, value: string): void;
}

export interface DurableVerificationEmailDelivery extends VerificationEmailDelivery {
  deliveryId: string;
}

export interface MailAppDeliveryReceipt {
  deliveryId: string;
  status: "PROVIDER_ACCEPTED" | "NO_OP";
  safeResultCode: "EMAIL_PROVIDER_ACCEPTED" | "EMAIL_DELIVERY_ALREADY_ACCEPTED";
  quotaRemainingBefore: number;
}

const deliveryIdPattern = /^email_delivery_[a-z0-9]{8,64}$/;
const challengeIdPattern = /^email_verification_[a-z0-9]{8,64}$/;
const emailPattern = /^[^\s@,]+@[^\s@,]+\.[^\s@,]+$/;
const codePattern = /^[0-9]{6}$/;

function validateDelivery(delivery: DurableVerificationEmailDelivery): void {
  if (
    !deliveryIdPattern.test(delivery.deliveryId) ||
    !challengeIdPattern.test(delivery.challengeId) ||
    !emailPattern.test(delivery.destination) ||
    delivery.destination.length > 254 ||
    !codePattern.test(delivery.code) ||
    (delivery.kind !== "INSTITUTIONAL" && delivery.kind !== "CONTACT") ||
    Number.isNaN(new Date(delivery.expiresAt).getTime())
  ) {
    throw new Error("EMAIL_DELIVERY_INVALID");
  }
  if (new Date(delivery.expiresAt).getTime() <= Date.now()) {
    throw new Error("EMAIL_CODE_EXPIRED");
  }
}

export type ExpiryFormatter = (expiresAt: string) => string;

const gasExpiryFormatter: ExpiryFormatter = (expiresAt) =>
  Utilities.formatDate(new Date(expiresAt), "Asia/Taipei", "yyyy-MM-dd HH:mm");

function messageBody(
  delivery: DurableVerificationEmailDelivery,
  formatExpiry: ExpiryFormatter,
): string {
  const expiry = formatExpiry(delivery.expiresAt);
  return [
    "你的微積分 Discord Portal 驗證碼是：",
    "",
    delivery.code,
    "",
    `此驗證碼將於 ${expiry}（台北時間）失效。`,
    "如果你沒有提出這項申請，請直接忽略這封信。",
    "",
    "本信由系統自動寄出，請勿回覆。",
  ].join("\n");
}

export class MailAppVerificationEmailProvider {
  constructor(
    private readonly mail: MailAppPort,
    private readonly receipts: DeliveryReceiptStore,
    private readonly quotaReserve: number,
    private readonly formatExpiry: ExpiryFormatter = gasExpiryFormatter,
  ) {
    if (
      !Number.isInteger(quotaReserve) ||
      quotaReserve < 1 ||
      quotaReserve > 1_000
    ) {
      throw new Error("EMAIL_QUOTA_RESERVE_INVALID");
    }
  }

  sendDurable(
    delivery: DurableVerificationEmailDelivery,
  ): MailAppDeliveryReceipt {
    validateDelivery(delivery);
    const existing = this.receipts.get(delivery.deliveryId);
    if (existing === "PROVIDER_ACCEPTED") {
      return {
        deliveryId: delivery.deliveryId,
        status: "NO_OP",
        safeResultCode: "EMAIL_DELIVERY_ALREADY_ACCEPTED",
        quotaRemainingBefore: -1,
      };
    }
    if (existing === "ATTEMPTING" || existing === "AMBIGUOUS") {
      throw new Error("EMAIL_DELIVERY_AMBIGUOUS");
    }
    const quota = this.mail.getRemainingDailyQuota();
    if (quota <= this.quotaReserve) throw new Error("EMAIL_QUOTA_RESERVED");

    this.receipts.set(delivery.deliveryId, "ATTEMPTING");
    try {
      this.mail.sendEmail(
        delivery.destination,
        "微積分 Discord Portal 驗證碼",
        messageBody(delivery, this.formatExpiry),
      );
    } catch {
      this.receipts.set(delivery.deliveryId, "AMBIGUOUS");
      throw new Error("EMAIL_DELIVERY_AMBIGUOUS");
    }
    this.receipts.set(delivery.deliveryId, "PROVIDER_ACCEPTED");
    return {
      deliveryId: delivery.deliveryId,
      status: "PROVIDER_ACCEPTED",
      safeResultCode: "EMAIL_PROVIDER_ACCEPTED",
      quotaRemainingBefore: quota,
    };
  }
}
