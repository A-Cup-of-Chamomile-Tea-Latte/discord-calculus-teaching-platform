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
  audience: "HUMAN" | "MACHINE";
  columns: readonly SheetColumn[];
  indexes: readonly string[];
  sensitiveFields: readonly string[];
  retention: string;
  sourceContracts: readonly string[];
}

export const SHEETS_SCHEMA_VERSION = "2.0.0";
export const SHEETS_SCHEMA_RELEASED_AT = "2026-08-10T22:30:00+08:00";

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

export const HUMAN_VIEW_SHEETS = [
  "Overview",
  "CaseBoard",
  "Members",
  "Operations",
  "History",
] as const;

export const MACHINE_VIEW_SHEETS = [
  "_CommandInbox",
  "_EmailOutbox",
  "_SyncState",
  "_Artifacts",
  "_Settings",
] as const;

export const LEGACY_FULL_SCHEMA_SHEETS = [
  "Users",
  "Emails",
  "DiscordAccounts",
  "CourseMemberships",
  "Cases",
  "Posts",
  "Consents",
  "ActiveCases",
  "CaseProjection",
  "SyncState",
  "ChangedCaseQueue",
  "CommandQueue",
  "EmailQueue",
  "ArchiveIndex",
  "ExportManifest",
  "SanitizedPackage",
  "WeeklyMaintenanceRun",
  "ActivationCodes",
  "Exports",
  "AuditLog",
  "Settings",
] as const;

export const LEGACY_MANAGED_SETTING_KEYS = [
  "schema.version",
  "schema.migration.last",
] as const;

export const SHEET_SCHEMAS: readonly SheetDefinition[] = [
  {
    name: "Overview",
    primaryKey: "metricKey",
    audience: "HUMAN",
    columns: [
      required("metricKey", "string"),
      optional("metricValue", "nullable-string"),
      required("status", "string"),
      required("description", "string"),
      optional("asOf", "nullable-timestamp"),
      optional("sourceReceipt", "nullable-string", true),
    ],
    indexes: ["metricKey (primary)", "status"],
    sensitiveFields: ["sourceReceipt"],
    retention:
      "Current sufficient statistics only; replace prior values instead of logging history.",
    sourceContracts: [
      "derived from CaseBoard, Members and Operations projections",
    ],
  },
  {
    name: "CaseBoard",
    primaryKey: "caseNumber",
    audience: "HUMAN",
    columns: [
      required("schemaVersion", "string"),
      required("caseNumber", "string"),
      required("moduleCode", "string"),
      required("status", "string"),
      optional("assignedAlias", "nullable-string"),
      required("actionNeeded", "string"),
      optional("lastStudentAt", "nullable-timestamp"),
      optional("lastStaffAt", "nullable-timestamp"),
      optional("nextDeadlineAt", "nullable-timestamp"),
      required("analysisEligible", "boolean"),
      required("updatedAt", "timestamp"),
      required("sourceVersion", "integer"),
      required("sourceChecksum", "string", true),
    ],
    indexes: [
      "caseNumber (primary)",
      "status + nextDeadlineAt",
      "assignedAlias + status",
    ],
    sensitiveFields: ["sourceChecksum"],
    retention:
      "Current reduced case state; raw posts and Private Support content stay outside Sheets.",
    sourceContracts: ["contracts/schemas/reduced-case-projection.schema.json"],
  },
  {
    name: "Members",
    primaryKey: "memberRef",
    audience: "HUMAN",
    columns: [
      required("schemaVersion", "string"),
      required("memberRef", "string", true),
      required("courseAlias", "string", true),
      required("role", "string"),
      required("membershipStatus", "string"),
      required("verificationStatus", "string"),
      required("analysisDefault", "string"),
      optional("joinedAt", "nullable-timestamp"),
      required("updatedAt", "timestamp"),
      required("sourceVersion", "integer"),
    ],
    indexes: ["memberRef (primary)", "role + membershipStatus", "courseAlias"],
    sensitiveFields: ["memberRef", "courseAlias"],
    retention:
      "Current membership projection only; names, student IDs and email addresses stay local.",
    sourceContracts: ["contracts/schemas/course-membership.schema.json"],
  },
  {
    name: "Operations",
    primaryKey: "operationKey",
    audience: "HUMAN",
    columns: [
      required("schemaVersion", "string"),
      required("operationKey", "string"),
      required("service", "string"),
      required("component", "string"),
      required("status", "string"),
      required("mode", "string"),
      optional("version", "nullable-string"),
      optional("lastHeartbeatAt", "nullable-timestamp"),
      optional("queueDepth", "integer"),
      optional("lastSuccessAt", "nullable-timestamp"),
      optional("safeErrorCode", "nullable-string"),
      optional("nextAction", "nullable-string"),
      required("checkedAt", "timestamp"),
    ],
    indexes: [
      "operationKey (primary)",
      "service + status",
      "status + checkedAt",
    ],
    sensitiveFields: [],
    retention:
      "Current service and queue health; detailed logs and process IDs stay local.",
    sourceContracts: ["runtime health receipts"],
  },
  {
    name: "History",
    primaryKey: "eventRef",
    audience: "HUMAN",
    columns: [
      required("schemaVersion", "string"),
      required("eventRef", "string", true),
      required("eventType", "string"),
      required("subjectType", "string"),
      required("subjectRef", "string", true),
      required("summaryCode", "string"),
      optional("fromState", "nullable-string"),
      optional("toState", "nullable-string"),
      required("occurredAt", "timestamp"),
      required("source", "string"),
      required("sourceReceipt", "string", true),
    ],
    indexes: [
      "eventRef (primary)",
      "subjectType + subjectRef + occurredAt",
      "eventType",
    ],
    sensitiveFields: ["eventRef", "subjectRef", "sourceReceipt"],
    retention:
      "Meaningful lifecycle transitions only; never raw messages or high-frequency debug logs.",
    sourceContracts: ["contracts/schemas/audit-event.schema.json"],
  },
  {
    name: "_CommandInbox",
    primaryKey: "jobRef",
    audience: "MACHINE",
    columns: [
      required("schemaVersion", "string"),
      required("jobRef", "string", true),
      required("commandType", "string"),
      required("payloadRef", "string", true),
      optional("targetRef", "nullable-string", true),
      required("status", "string"),
      required("idempotencyKey", "string", true),
      optional("claimedBy", "nullable-string", true),
      optional("leaseExpiresAt", "nullable-timestamp"),
      required("attemptCount", "integer"),
      optional("retryAt", "nullable-timestamp"),
      optional("safeErrorCode", "nullable-string"),
      required("createdAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: [
      "jobRef (primary)",
      "idempotencyKey (unique)",
      "status + retryAt",
    ],
    sensitiveFields: [
      "jobRef",
      "payloadRef",
      "targetRef",
      "idempotencyKey",
      "claimedBy",
    ],
    retention:
      "Pending work plus a short receipt window; payload content and credentials stay outside Sheets.",
    sourceContracts: ["contracts/schemas/command-queue.schema.json"],
  },
  {
    name: "_EmailOutbox",
    primaryKey: "jobRef",
    audience: "MACHINE",
    columns: [
      required("schemaVersion", "string"),
      required("jobRef", "string", true),
      required("emailType", "string"),
      required("recipientRef", "string", true),
      required("templateKey", "string"),
      required("contentRef", "string", true),
      required("status", "string"),
      required("idempotencyKey", "string", true),
      optional("claimedBy", "nullable-string", true),
      optional("leaseExpiresAt", "nullable-timestamp"),
      required("attemptCount", "integer"),
      optional("retryAt", "nullable-timestamp"),
      optional("providerAcceptedAt", "nullable-timestamp"),
      optional("safeErrorCode", "nullable-string"),
      required("createdAt", "timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: [
      "jobRef (primary)",
      "idempotencyKey (unique)",
      "status + retryAt",
    ],
    sensitiveFields: [
      "jobRef",
      "recipientRef",
      "contentRef",
      "idempotencyKey",
      "claimedBy",
    ],
    retention:
      "Delivery metadata only; no email address, subject, body, code or credential.",
    sourceContracts: ["contracts/schemas/email-queue.schema.json"],
  },
  {
    name: "_SyncState",
    primaryKey: "syncKey",
    audience: "MACHINE",
    columns: [
      required("schemaVersion", "string"),
      required("syncKey", "string", true),
      required("direction", "string"),
      required("sourceName", "string"),
      required("sourceVersion", "integer"),
      required("sourceChecksum", "string", true),
      optional("cursorRef", "nullable-string", true),
      required("status", "string"),
      optional("lastAttemptAt", "nullable-timestamp"),
      optional("lastSuccessAt", "nullable-timestamp"),
      optional("safeErrorCode", "nullable-string"),
      optional("operatorConfirmedAt", "nullable-timestamp"),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["syncKey (primary)", "direction + status", "status + updatedAt"],
    sensitiveFields: ["syncKey", "sourceChecksum", "cursorRef"],
    retention:
      "Latest authenticity and cursor receipt only; not a change-history table.",
    sourceContracts: ["local/cloud projection authenticity gate"],
  },
  {
    name: "_Artifacts",
    primaryKey: "artifactRef",
    audience: "MACHINE",
    columns: [
      required("schemaVersion", "string"),
      required("artifactRef", "string", true),
      required("artifactType", "string"),
      optional("caseRef", "nullable-string", true),
      required("storageKind", "string"),
      required("locationRef", "string", true),
      required("contentSha256", "string"),
      required("sanitizationStatus", "string"),
      required("containsPrivateSupport", "boolean"),
      required("createdAt", "timestamp"),
      optional("retentionReviewAt", "nullable-timestamp"),
      required("state", "string"),
    ],
    indexes: [
      "artifactRef (primary)",
      "artifactType + state",
      "caseRef + createdAt",
    ],
    sensitiveFields: ["artifactRef", "caseRef", "locationRef"],
    retention:
      "Index and checksum only; payload remains in its governed file carrier.",
    sourceContracts: ["contracts/schemas/export-manifest.schema.json"],
  },
  {
    name: "_Settings",
    primaryKey: "settingKey",
    audience: "MACHINE",
    columns: [
      required("settingKey", "string"),
      required("settingValue", "string", true),
      required("valueClass", "string"),
      required("description", "string"),
      required("updatedAt", "timestamp"),
    ],
    indexes: ["settingKey (primary)"],
    sensitiveFields: [
      "settingValue (PUBLIC/INTERNAL/SECRET_REF_ONLY; never a secret value)",
    ],
    retention: "Current non-secret configuration and schema receipts only.",
    sourceContracts: ["apps/gas compact cloud projection schema"],
  },
] as const;

export const SCHEMA_METADATA_ROWS = [
  {
    settingKey: "schema.version",
    settingValue: SHEETS_SCHEMA_VERSION,
    valueClass: "PUBLIC",
    description: "Current compact cloud projection schema version",
    updatedAt: SHEETS_SCHEMA_RELEASED_AT,
  },
  {
    settingKey: "schema.migration.last",
    settingValue: "0005-compact-sufficient-statistics",
    valueClass: "PUBLIC",
    description: "Last idempotent migration applied by bootstrap",
    updatedAt: SHEETS_SCHEMA_RELEASED_AT,
  },
  {
    settingKey: "data.authority",
    settingValue: "LOCAL_PRIMARY_CLOUD_PROJECTION",
    valueClass: "PUBLIC",
    description:
      "Local SQLite is primary; cloud imports require authenticity checks and confirmation",
    updatedAt: SHEETS_SCHEMA_RELEASED_AT,
  },
] as const;

export function headersFor(definition: SheetDefinition): string[] {
  return definition.columns.map((column) => column.name);
}
