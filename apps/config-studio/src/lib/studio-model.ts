export interface PermissionDecision {
  allow: string[];
  deny: string[];
}

export interface StudioChannel {
  key: string;
  name: string;
  type: "TEXT" | "FORUM" | "VOICE";
  parent: string;
  topic: string;
  slowmodeSeconds: number;
  autoArchiveMinutes: number;
  enabled: boolean;
  managedCase: boolean;
  forumTags: string[];
  permissions: Record<string, PermissionDecision>;
}

export interface StudioRole {
  key: string;
  name: string;
  kind: "STAFF" | "LEARNER" | "BOT" | "ATTRIBUTE";
  hierarchy: number;
  publiclyDisplayed: boolean;
  databaseOnly: boolean;
}

export interface StudioCategory {
  key: string;
  name: string;
  enabled: boolean;
}

export interface StudioServerConfig {
  status: string;
  source: {
    package: string;
    document: string;
    note: string;
  };
  roles: StudioRole[];
  categories: StudioCategory[];
  channels: StudioChannel[];
  botPermissions: Array<{
    key: string;
    permissions: string[];
    scopedAreas: string[];
  }>;
}

export interface StudioPortalConfig {
  status: string;
  defaultTheme: string;
  pages: Array<{
    key: string;
    path: string;
    label: string;
    audience: string;
    enabled: boolean;
  }>;
}

export interface WorkflowState {
  key: string;
  label: string;
  description: string;
}

export interface StudioWorkflowConfig {
  status: string;
  canonicalTitle: {
    pattern: string;
    modules: string[];
    mainTags: string[];
    mainTagsFinalized: boolean;
    manualClosePrefix: string;
    automaticClosePrefix: string;
  };
  states: WorkflowState[];
  transitions: Array<{
    from: string;
    to: string;
    event: string;
    actor: string;
  }>;
  timers: {
    idleAfterHours: number;
    autoCloseAfterIdleHours: number;
    startFrom: string;
  };
  privateSupport: {
    transport: string;
    capacityThreshold: number;
    visibleRoles: string[];
    closeSequence: string[];
    reopenUi: string;
  };
}

export interface AcademicModule {
  moduleCode: "M1" | "M2" | "M3" | "M4";
  displayName: string;
  classCodes: string[];
}

export interface AcademicPerson {
  publicDisplayName: string;
}

export interface AcademicTaAssignment {
  taRef: string;
  categoryCode: "L" | "G" | "G_L" | "UNSPECIFIED";
}

export interface AcademicTaCategory {
  code: AcademicTaAssignment["categoryCode"];
  meaning:
    "TA_LECTURER" | "TA_GRADER" | "TA_LECTURER_AND_TA_GRADER" | "SOURCE_BLANK";
  discordRoleKeys: Array<"ta_lecturer" | "ta_grader">;
}

export interface AcademicPracticeSection {
  practiceSectionKey: string;
  taRef: string;
  room: string;
  assignmentRule:
    | { kind: "ALL_STUDENTS" }
    | {
        kind: "STUDENT_ID_LAST_THREE_MODULO_PRACTICE_TA_COUNT";
        remainder: number;
      };
}

export interface AcademicClassSection {
  classCode: string;
  sourceLabel: string;
  canonicalClassLabel: string;
  moduleCode: AcademicModule["moduleCode"] | null;
  status: "ACTIVE" | "REFERENCE_ONLY_PENDING_CONFIRMATION";
  instructorRef: string;
  taAssignments: AcademicTaAssignment[];
  practiceSections: AcademicPracticeSection[];
  note?: string;
}

export interface StudioAcademicConfig {
  status: "SOURCE_CONFIRMED";
  term: {
    termCode: string;
    displayName: string;
  };
  modules: AcademicModule[];
  taCategoryCodes: AcademicTaCategory[];
  peopleDirectory: {
    instructors: Array<AcademicPerson & { instructorRef: string }>;
    teachingAssistants: Array<AcademicPerson & { taRef: string }>;
  };
  sections: AcademicClassSection[];
  referenceOnlySections: AcademicClassSection[];
}

export interface StudioBundle {
  server: StudioServerConfig;
  portal: StudioPortalConfig;
  workflow: StudioWorkflowConfig;
  dataPolicy: Record<string, unknown>;
  academic: StudioAcademicConfig;
}

export type DiffKind =
  "ADD" | "MODIFY" | "REMOVE" | "UNCHANGED" | "NEEDS_APPROVAL";

export interface StudioDiff {
  kind: DiffKind;
  key: string;
  detail: string;
}

export function cloneBundle(bundle: StudioBundle): StudioBundle {
  return structuredClone(bundle);
}

export function computeChannelDiff(
  original: StudioChannel[],
  current: StudioChannel[],
): StudioDiff[] {
  const originalByKey = new Map(
    original.map((channel) => [channel.key, channel]),
  );
  const currentByKey = new Map(
    current.map((channel) => [channel.key, channel]),
  );
  const keys = [
    ...new Set([...originalByKey.keys(), ...currentByKey.keys()]),
  ].sort();
  return keys.map((key) => {
    const before = originalByKey.get(key);
    const after = currentByKey.get(key);
    if (!before && after)
      return { kind: "ADD", key, detail: `將新增 ${after.name}` };
    if (before && !after)
      return { kind: "REMOVE", key, detail: `將移除 ${before.name}` };
    if (JSON.stringify(before) !== JSON.stringify(after)) {
      return {
        kind: "MODIFY",
        key,
        detail: `將修改 ${after?.name ?? before?.name}`,
      };
    }
    return { kind: "UNCHANGED", key, detail: `${after?.name ?? key} 無變更` };
  });
}

export function canonicalTitlePreview(
  module: string,
  classCode: string,
  mainTag: string,
  title: string,
): string {
  const normalizedTitle = title.trim() || "我不懂 chain rule";
  const normalizedTag = mainTag.trim() || "觀念";
  const normalizedClass = classCode.trim().replace(/^C/i, "").padStart(2, "0");
  return `[${module} | C${normalizedClass}][${normalizedTag}] ${normalizedTitle}`;
}

export function classifyImport(
  kind: string,
  content: string,
): { accepted: boolean; message: string } {
  if (!kind) return { accepted: false, message: "請先指定文件性質。" };
  if (!content.trim())
    return { accepted: false, message: "請貼上或匯入內容。" };
  if (content.length > 250_000)
    return { accepted: false, message: "內容超過本機預覽上限（250 KB）。" };
  return {
    accepted: true,
    message: `已載入 ${content.length.toLocaleString("zh-Hant")} 個字元；僅供預覽，不會自動合併。`,
  };
}
