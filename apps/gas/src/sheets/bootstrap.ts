import {
  headersFor,
  LEGACY_FULL_SCHEMA_SHEETS,
  LEGACY_MANAGED_SETTING_KEYS,
  SCHEMA_METADATA_ROWS,
  SHEET_SCHEMAS,
} from "./schema";

export type SheetCell = string | number | boolean | null;
export type SheetRecord = Record<string, SheetCell>;

export interface SheetPort {
  getHeaders(): string[];
  getRows(): SheetRecord[];
  hasDataFormulas(): boolean;
  getDataRowCount(): number;
  getColumnValues(header: string): string[];
  appendHeaders(headers: readonly string[]): void;
  getRowByPrimaryKey(primaryKey: string, value: string): SheetRecord | null;
  upsertRowByPrimaryKey(
    primaryKey: string,
    value: string,
    record: SheetRecord,
  ): "inserted" | "updated" | "unchanged";
  deleteRowByPrimaryKey(primaryKey: string, value: string): boolean;
}

export interface WorkbookPort {
  getSheet(name: string): SheetPort | null;
  createSheet(name: string): SheetPort;
  deleteSheet(name: string): void;
  listSheetNames(): string[];
}

export type BootstrapAction =
  | { type: "CREATE_SHEET"; sheet: string }
  | { type: "APPEND_HEADERS"; sheet: string; headers: string[] }
  | {
      type: "UPSERT_SCHEMA_METADATA";
      sheet: "_Settings";
      settingKey: string;
      change: "insert" | "update";
    };

export type CompactMigrationAction =
  BootstrapAction | { type: "DELETE_EMPTY_LEGACY_SHEET"; sheet: string };

export interface BootstrapResult {
  dryRun: boolean;
  actions: BootstrapAction[];
  changed: boolean;
}

export interface CompactMigrationResult {
  dryRun: boolean;
  actions: CompactMigrationAction[];
  blockers: string[];
  changed: boolean;
}

function recordMatches(existing: SheetRecord, desired: SheetRecord): boolean {
  return Object.entries(desired).every(
    ([key, value]) => existing[key] === value,
  );
}

export function bootstrapWorkbook(
  workbook: WorkbookPort,
  options: { dryRun: boolean } = { dryRun: true },
): BootstrapResult {
  const actions: BootstrapAction[] = [];

  for (const definition of SHEET_SCHEMAS) {
    let sheet = workbook.getSheet(definition.name);
    if (!sheet) {
      actions.push({ type: "CREATE_SHEET", sheet: definition.name });
      if (!options.dryRun) sheet = workbook.createSheet(definition.name);
    }

    const existingHeaders = sheet?.getHeaders() ?? [];
    const missingHeaders = headersFor(definition).filter(
      (header) => !existingHeaders.includes(header),
    );
    if (missingHeaders.length > 0) {
      actions.push({
        type: "APPEND_HEADERS",
        sheet: definition.name,
        headers: missingHeaders,
      });
      if (!options.dryRun) sheet?.appendHeaders(missingHeaders);
    }

    if (definition.name !== "_Settings") continue;
    for (const metadata of SCHEMA_METADATA_ROWS) {
      const desired: SheetRecord = { ...metadata };
      const existing = sheet?.getRowByPrimaryKey(
        definition.primaryKey,
        metadata.settingKey,
      );
      if (existing && recordMatches(existing, desired)) continue;
      actions.push({
        type: "UPSERT_SCHEMA_METADATA",
        sheet: "_Settings",
        settingKey: metadata.settingKey,
        change: existing ? "update" : "insert",
      });
      if (!options.dryRun) {
        sheet?.upsertRowByPrimaryKey(
          definition.primaryKey,
          metadata.settingKey,
          desired,
        );
      }
    }
  }

  return { dryRun: options.dryRun, actions, changed: actions.length > 0 };
}

function legacyMigrationBlockers(workbook: WorkbookPort): string[] {
  const blockers: string[] = [];
  const allowedSettings = new Set<string>(LEGACY_MANAGED_SETTING_KEYS);
  for (const name of LEGACY_FULL_SCHEMA_SHEETS) {
    const sheet = workbook.getSheet(name);
    if (!sheet || sheet.getDataRowCount() === 0) continue;
    if (name === "Settings") {
      const unknownKeys = sheet
        .getColumnValues("settingKey")
        .filter((key) => key && !allowedSettings.has(key));
      if (unknownKeys.length === 0) continue;
      blockers.push(
        `Settings contains operator-owned keys: ${unknownKeys.join(", ")}`,
      );
      continue;
    }
    blockers.push(`${name} contains ${sheet.getDataRowCount()} data row(s)`);
  }
  return blockers;
}

export function migrateToCompactWorkbook(
  workbook: WorkbookPort,
  options: { dryRun: boolean } = { dryRun: true },
): CompactMigrationResult {
  const blockers = legacyMigrationBlockers(workbook);
  if (blockers.length > 0) {
    return {
      dryRun: options.dryRun,
      actions: [],
      blockers,
      changed: false,
    };
  }

  const bootstrap = bootstrapWorkbook(workbook, { dryRun: options.dryRun });
  const existingNames = new Set(workbook.listSheetNames());
  const deleteActions: CompactMigrationAction[] =
    LEGACY_FULL_SCHEMA_SHEETS.filter((name) => existingNames.has(name)).map(
      (sheet) => ({ type: "DELETE_EMPTY_LEGACY_SHEET", sheet }),
    );

  if (!options.dryRun) {
    for (const action of deleteActions) workbook.deleteSheet(action.sheet);
  }
  const actions = [...bootstrap.actions, ...deleteActions];
  return {
    dryRun: options.dryRun,
    actions,
    blockers: [],
    changed: actions.length > 0,
  };
}
