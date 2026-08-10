export type SheetValueType =
  | "string"
  | "integer"
  | "boolean"
  | "timestamp"
  | "nullable-string"
  | "nullable-timestamp"
  | "json";

export interface SheetColumn {
  name: string;
  type: SheetValueType;
  required: boolean;
  sensitive?: boolean;
}

export interface SheetDefinition {
  name: string;
  primaryKey: string;
  columns: readonly SheetColumn[];
  indexes: readonly string[];
  sensitiveFields: readonly string[];
  retention: string;
  sourceContracts: readonly string[];
}

export const SHEETS_SCHEMA_VERSION = "1.3.0";
export const SHEETS_SCHEMA_RELEASED_AT = "2026-08-10T00:00:00+08:00";

const required = (
  name: string,
  type: SheetValueType,
  sensitive = false,
): SheetColumn => ({ name, type, required: true, sensitive });

const optional = (
  name: string,
  type: SheetValueType,
  sensitive = false,
): SheetColumn => ({ name, type, required: false, sensitive });

export const SHEET_SCHEMAS: readonly SheetDefinition[] = [
  {
    name: "Users",
    primaryKey: "userId",
    columns: [
      required("schemaVersion", "string"),
      required("userId", "string", true),
      required("displayLabel", "string", true),
      required("defaultAuthorDisplayMode", "string"),
      required("analysisPermissionDefault", "string"),
      required("verifiedEmailIdsJson", "json", true),
      required("discordAccountIdsJson", "json", true),
      required("membershipIdsJson", "json", true),
      required("createdAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["userId (primary)", "displayLabel"],
    sensitiveFields: [
      "userId",
      "displayLabel",
      "verifiedEmailIdsJson",
      "discordAccountIdsJson",
      "membershipIdsJson",
    ],
    retention:
      "Account lifetime plus approved deletion/audit window; policy pending Task 29.",
    sourceContracts: ["contracts/schemas/user.schema.json"],
  },
  {
    name: "Emails",
    primaryKey: "verifiedEmailId",
    columns: [
      required("schemaVersion", "string"),
      required("verifiedEmailId", "string", true),
      required("userId", "string", true),
      required("email", "string", true),
      required("kind", "string"),
      required("verifiedAt", "timestamp"),
      required("isPrimary", "boolean"),
      required("createdAt", "timestamp"),
    ],
    indexes: [
      "verifiedEmailId (primary)",
      "email (unique)",
      "userId",
      "userId + isPrimary",
    ],
    sensitiveFields: ["verifiedEmailId", "userId", "email"],
    retention:
      "Keep only while needed for membership/contact and approved audit window.",
    sourceContracts: ["contracts/schemas/verified-email.schema.json"],
  },
  {
    name: "DiscordAccounts",
    primaryKey: "discordAccountId",
    columns: [
      required("schemaVersion", "string"),
      required("discordAccountId", "string", true),
      required("userId", "string", true),
      required("discordUserId", "string", true),
      required("globalUsername", "string", true),
      optional("globalDisplayName", "nullable-string", true),
      required("linkedAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["discordAccountId (primary)", "discordUserId (unique)", "userId"],
    sensitiveFields: [
      "discordAccountId",
      "userId",
      "discordUserId",
      "globalUsername",
      "globalDisplayName",
    ],
    retention:
      "Remove link when account is unlinked, subject to minimal audit retention.",
    sourceContracts: ["contracts/schemas/discord-account.schema.json"],
  },
  {
    name: "CourseMemberships",
    primaryKey: "membershipId",
    columns: [
      required("schemaVersion", "string"),
      required("membershipId", "string", true),
      required("userId", "string", true),
      required("courseId", "string"),
      required("classCode", "string"),
      required("joiningOrder", "integer"),
      required("courseAlias", "string", true),
      required("verificationMethod", "string", true),
      required("status", "string"),
      required("joinedAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: [
      "membershipId (primary)",
      "userId + courseId (unique)",
      "courseId + courseAlias (unique)",
      "courseId + classCode + status",
    ],
    sensitiveFields: [
      "membershipId",
      "userId",
      "courseAlias",
      "verificationMethod",
    ],
    retention:
      "Course term plus approved support/audit window; deactivate rather than delete during term.",
    sourceContracts: ["contracts/schemas/course-membership.schema.json"],
  },
  {
    name: "Cases",
    primaryKey: "caseId",
    columns: [
      required("schemaVersion", "string"),
      required("caseId", "string", true),
      optional("caseNumber", "nullable-string"),
      required("caseType", "string"),
      required("status", "string"),
      required("visibility", "string"),
      required("authorDisplayMode", "string"),
      required("analysisPermission", "string"),
      required("createdByUserId", "string", true),
      optional("classCode", "nullable-string"),
      required("title", "string", true),
      required("source", "string"),
      optional("discordMappingJson", "json", true),
      required("createdAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: [
      "caseId (primary)",
      "caseNumber (unique when non-null)",
      "status + updatedAt",
      "createdByUserId",
      "caseType + visibility",
    ],
    sensitiveFields: [
      "caseId",
      "createdByUserId",
      "title",
      "discordMappingJson",
    ],
    retention:
      "Case lifecycle plus approved appeal/audit window; Private Support policy is stricter.",
    sourceContracts: ["contracts/schemas/case.schema.json"],
  },
  {
    name: "Posts",
    primaryKey: "messageId",
    columns: [
      required("schemaVersion", "string"),
      required("messageId", "string", true),
      required("caseId", "string", true),
      required("authorUserId", "string", true),
      required("authorRole", "string"),
      required("authorDisplayMode", "string"),
      required("body", "string", true),
      required("source", "string"),
      required("analysisPermission", "string"),
      optional("parentMessageId", "nullable-string"),
      optional("discordMessageId", "nullable-string", true),
      optional("editedAt", "nullable-timestamp"),
      required("attachmentsJson", "json", true),
      required("createdAt", "timestamp"),
    ],
    indexes: [
      "messageId (primary)",
      "caseId + createdAt",
      "discordMessageId (unique when non-null)",
      "authorUserId + createdAt",
    ],
    sensitiveFields: [
      "messageId",
      "caseId",
      "authorUserId",
      "body",
      "discordMessageId",
      "attachmentsJson",
    ],
    retention:
      "Only curated case posts; never synchronous full Discord history. Policy pending Task 29.",
    sourceContracts: ["contracts/schemas/case-message.schema.json"],
  },
  {
    name: "Consents",
    primaryKey: "consentId",
    columns: [
      required("schemaVersion", "string"),
      required("consentId", "string", true),
      required("userId", "string", true),
      required("scope", "string"),
      required("accountDefault", "string"),
      required("perPostOverridesJson", "json", true),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["consentId (primary)", "userId + scope (unique)", "updatedAt"],
    sensitiveFields: ["consentId", "userId", "perPostOverridesJson"],
    retention:
      "Current decision plus change/audit history required to prove consent state.",
    sourceContracts: ["contracts/schemas/consent.schema.json"],
  },
  {
    name: "ActiveCases",
    primaryKey: "caseId",
    columns: [
      required("schemaVersion", "string"),
      required("caseId", "string", true),
      required("status", "string"),
      required("projectionVersion", "integer"),
      optional("sourceCursor", "nullable-string", true),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["caseId (primary)", "status + updatedAt"],
    sensitiveFields: ["caseId", "sourceCursor"],
    retention:
      "Working set only; closed rows roll over after the reviewed weekly plan.",
    sourceContracts: ["contracts/schemas/active-case.schema.json"],
  },
  {
    name: "CaseProjection",
    primaryKey: "caseId",
    columns: [
      required("schemaVersion", "string"),
      required("caseId", "string", true),
      required("projectionVersion", "integer"),
      required("projectionJson", "json", true),
      required("lastSyncedAt", "timestamp"),
    ],
    indexes: ["caseId (primary)", "lastSyncedAt"],
    sensitiveFields: ["caseId", "projectionJson"],
    retention:
      "Incremental web-query projection; never recompute full history on request.",
    sourceContracts: ["contracts/schemas/reduced-case-projection.schema.json"],
  },
  {
    name: "SyncState",
    primaryKey: "syncKey",
    columns: [
      required("schemaVersion", "string"),
      required("syncKey", "string", true),
      required("source", "string"),
      optional("cursor", "nullable-string", true),
      required("lastSyncedAt", "timestamp"),
      required("status", "string"),
      optional("errorCode", "nullable-string"),
    ],
    indexes: ["syncKey (primary)", "status + lastSyncedAt"],
    sensitiveFields: ["syncKey", "cursor"],
    retention:
      "Current incremental cursor only; do not treat as archive history.",
    sourceContracts: ["contracts/schemas/sync-state.schema.json"],
  },
  {
    name: "ChangedCaseQueue",
    primaryKey: "queueId",
    columns: [
      required("schemaVersion", "string"),
      required("queueId", "string", true),
      required("caseId", "string", true),
      required("changeVersion", "integer"),
      required("reason", "string"),
      required("enqueuedAt", "timestamp"),
      required("state", "string"),
      required("idempotencyKey", "string", true),
    ],
    indexes: [
      "queueId (primary)",
      "state + enqueuedAt",
      "idempotencyKey (unique)",
    ],
    sensitiveFields: ["queueId", "caseId", "idempotencyKey"],
    retention:
      "Delete applied fixture queue entries after bounded reconciliation.",
    sourceContracts: ["contracts/schemas/changed-case-queue.schema.json"],
  },
  {
    name: "CommandQueue",
    primaryKey: "commandId",
    columns: [
      required("schemaVersion", "string"),
      required("commandId", "string", true),
      required("commandType", "string"),
      required("payloadJson", "json", true),
      optional("targetUserId", "nullable-string", true),
      optional("targetCaseId", "nullable-string", true),
      required("status", "string"),
      required("idempotencyKey", "string", true),
      optional("claimedBy", "nullable-string", true),
      optional("leaseExpiresAt", "nullable-timestamp"),
      required("attemptCount", "integer"),
      optional("retryAt", "nullable-timestamp"),
      optional("resultJson", "json", true),
      optional("errorCode", "nullable-string"),
      required("createdAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: [
      "commandId (primary)",
      "idempotencyKey (unique)",
      "status + retryAt",
      "claimedBy + leaseExpiresAt",
    ],
    sensitiveFields: [
      "commandId",
      "payloadJson",
      "targetUserId",
      "targetCaseId",
      "idempotencyKey",
      "claimedBy",
      "resultJson",
    ],
    retention:
      "Working command state plus an approved minimal audit window; never store credentials or bot tokens.",
    sourceContracts: ["contracts/schemas/command-queue.schema.json"],
  },
  {
    name: "EmailQueue",
    primaryKey: "emailJobId",
    columns: [
      required("schemaVersion", "string"),
      required("emailJobId", "string", true),
      required("emailType", "string"),
      required("recipientEmailId", "string", true),
      required("templateKey", "string"),
      required("contentReference", "string", true),
      required("status", "string"),
      required("idempotencyKey", "string", true),
      optional("claimedBy", "nullable-string", true),
      optional("leaseExpiresAt", "nullable-timestamp"),
      required("attemptCount", "integer"),
      optional("retryAt", "nullable-timestamp"),
      optional("providerAcceptedAt", "nullable-timestamp"),
      optional("providerReceiptJson", "json", true),
      optional("errorCode", "nullable-string"),
      required("createdAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: [
      "emailJobId (primary)",
      "idempotencyKey (unique)",
      "status + retryAt",
      "claimedBy + leaseExpiresAt",
      "recipientEmailId + createdAt",
    ],
    sensitiveFields: [
      "emailJobId",
      "recipientEmailId",
      "contentReference",
      "idempotencyKey",
      "claimedBy",
      "providerReceiptJson",
    ],
    retention:
      "Working delivery metadata plus an approved minimal audit window; never store message bodies, verification codes, or credentials.",
    sourceContracts: ["contracts/schemas/email-queue.schema.json"],
  },
  {
    name: "ArchiveIndex",
    primaryKey: "archiveId",
    columns: [
      required("schemaVersion", "string"),
      required("archiveId", "string", true),
      required("caseId", "string", true),
      required("period", "string"),
      required("manifestId", "string", true),
      optional("sanitizedPackageId", "nullable-string", true),
      required("archivedAt", "timestamp"),
      required("state", "string"),
    ],
    indexes: ["archiveId (primary)", "caseId + period", "period + state"],
    sensitiveFields: [
      "archiveId",
      "caseId",
      "manifestId",
      "sanitizedPackageId",
    ],
    retention:
      "Long-term index only; payload lives outside the working workbook.",
    sourceContracts: ["contracts/schemas/archive-index.schema.json"],
  },
  {
    name: "ExportManifest",
    primaryKey: "exportId",
    columns: [
      required("schemaVersion", "string"),
      required("exportId", "string", true),
      required("caseId", "string", true),
      required("mode", "string"),
      required("messageCount", "integer"),
      required("filesJson", "json", true),
      required("createdAt", "timestamp"),
      required("completedAt", "timestamp"),
    ],
    indexes: ["exportId (primary)", "caseId + createdAt"],
    sensitiveFields: ["exportId", "caseId", "filesJson"],
    retention:
      "Immutable archive manifest; no exported message bodies in this sheet.",
    sourceContracts: ["contracts/schemas/export-manifest.schema.json"],
  },
  {
    name: "SanitizedPackage",
    primaryKey: "packageId",
    columns: [
      required("schemaVersion", "string"),
      required("packageId", "string", true),
      required("sourceExportId", "string", true),
      required("contentSha256", "string"),
      required("caseCount", "integer"),
      required("createdAt", "timestamp"),
      required("reviewState", "string"),
      required("containsPrivateSupport", "boolean"),
    ],
    indexes: [
      "packageId (primary)",
      "sourceExportId",
      "reviewState + createdAt",
    ],
    sensitiveFields: ["packageId", "sourceExportId"],
    retention: "Long-term only after explicit sanitization review approval.",
    sourceContracts: ["contracts/schemas/sanitized-package.schema.json"],
  },
  {
    name: "WeeklyMaintenanceRun",
    primaryKey: "runId",
    columns: [
      required("schemaVersion", "string"),
      required("runId", "string", true),
      required("scheduledFor", "timestamp"),
      required("state", "string"),
      required("plannedActionsJson", "json"),
      required("dryRun", "boolean"),
      required("createdAt", "timestamp"),
      optional("completedAt", "nullable-timestamp"),
      required("estimatedWrites", "integer"),
    ],
    indexes: ["runId (primary)", "scheduledFor + state"],
    sensitiveFields: ["runId"],
    retention: "Minimal maintenance audit; never include case contents.",
    sourceContracts: ["contracts/schemas/weekly-maintenance-run.schema.json"],
  },
  {
    name: "ActivationCodes",
    primaryKey: "activationCodeId",
    columns: [
      required("schemaVersion", "string"),
      required("activationCodeId", "string", true),
      required("verifierHash", "string", true),
      required("status", "string"),
      required("createdByUserId", "string", true),
      required("bindingKind", "string", true),
      optional("bindingValueHash", "nullable-string", true),
      required("permissionProfileJson", "json", true),
      optional("redeemedByUserId", "nullable-string", true),
      required("createdAt", "timestamp"),
      required("expiresAt", "timestamp"),
      optional("redeemedAt", "nullable-timestamp"),
      optional("revokedAt", "nullable-timestamp"),
      optional("redemptionRequestHash", "nullable-string", true),
    ],
    indexes: [
      "activationCodeId (primary)",
      "verifierHash (unique)",
      "status + expiresAt",
      "redeemedByUserId",
    ],
    sensitiveFields: [
      "activationCodeId",
      "verifierHash",
      "createdByUserId",
      "bindingKind",
      "bindingValueHash",
      "permissionProfileJson",
      "redeemedByUserId",
      "redemptionRequestHash",
    ],
    retention:
      "Short-lived verifier metadata plus minimal redemption/revocation audit; never plaintext nonce.",
    sourceContracts: ["contracts/schemas/activation-code.schema.json"],
  },
  {
    name: "Exports",
    primaryKey: "exportId",
    columns: [
      required("schemaVersion", "string"),
      required("exportId", "string", true),
      required("caseId", "string", true),
      required("caseType", "string"),
      required("initiatedByUserId", "string", true),
      required("mode", "string"),
      required("analysisPermission", "string"),
      required("messageCount", "integer"),
      optional("cursor", "nullable-string", true),
      required("filesJson", "json", true),
      required("createdAt", "timestamp"),
      required("completedAt", "timestamp"),
    ],
    indexes: [
      "exportId (primary)",
      "caseId + createdAt",
      "initiatedByUserId + createdAt",
    ],
    sensitiveFields: [
      "exportId",
      "caseId",
      "initiatedByUserId",
      "cursor",
      "filesJson",
    ],
    retention:
      "Manifest/audit only; exported files remain local and follow a separate deletion policy.",
    sourceContracts: ["contracts/schemas/export-manifest.schema.json"],
  },
  {
    name: "AuditLog",
    primaryKey: "eventId",
    columns: [
      required("schemaVersion", "string"),
      required("eventId", "string", true),
      required("eventType", "string"),
      optional("actorUserId", "nullable-string", true),
      required("subjectType", "string"),
      required("subjectId", "string", true),
      required("source", "string"),
      required("metadataJson", "json", true),
      required("occurredAt", "timestamp"),
    ],
    indexes: [
      "eventId (primary)",
      "subjectType + subjectId + occurredAt",
      "actorUserId + occurredAt",
      "eventType + occurredAt",
    ],
    sensitiveFields: ["actorUserId", "subjectId", "metadataJson"],
    retention:
      "Security/audit window only; do not use for high-frequency event logging.",
    sourceContracts: ["contracts/schemas/audit-event.schema.json"],
  },
  {
    name: "Settings",
    primaryKey: "settingKey",
    columns: [
      required("settingKey", "string"),
      required("settingValue", "string", true),
      required("description", "string"),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["settingKey (primary)"],
    sensitiveFields: ["settingValue (must never contain secrets)"],
    retention:
      "Keep current schema metadata; append migration records, never store runtime secrets.",
    sourceContracts: ["apps/gas local operational schema"],
  },
] as const;

export const SCHEMA_METADATA_ROWS = [
  {
    settingKey: "schema.version",
    settingValue: SHEETS_SCHEMA_VERSION,
    description: "Current non-destructive Sheets schema version",
    updatedAt: SHEETS_SCHEMA_RELEASED_AT,
  },
  {
    settingKey: "schema.migration.last",
    settingValue: "0004-command-email-queues",
    description: "Last idempotent migration applied by bootstrap",
    updatedAt: SHEETS_SCHEMA_RELEASED_AT,
  },
] as const;

export function headersFor(definition: SheetDefinition): string[] {
  return definition.columns.map((column) => column.name);
}
