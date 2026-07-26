import { headersFor, SCHEMA_METADATA_ROWS, SHEET_SCHEMAS } from "./schema";

export type SheetCell = string | number | boolean | null;
export type SheetRecord = Record<string, SheetCell>;

export interface SheetPort {
  getHeaders(): string[];
  appendHeaders(headers: readonly string[]): void;
  getRowByPrimaryKey(primaryKey: string, value: string): SheetRecord | null;
  upsertRowByPrimaryKey(
    primaryKey: string,
    value: string,
    record: SheetRecord,
  ): "inserted" | "updated" | "unchanged";
}

export interface WorkbookPort {
  getSheet(name: string): SheetPort | null;
  createSheet(name: string): SheetPort;
}

export type BootstrapAction =
  | { type: "CREATE_SHEET"; sheet: string }
  | { type: "APPEND_HEADERS"; sheet: string; headers: string[] }
  | {
      type: "UPSERT_SCHEMA_METADATA";
      sheet: "Settings";
      settingKey: string;
      change: "insert" | "update";
    };

export interface BootstrapResult {
  dryRun: boolean;
  actions: BootstrapAction[];
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

    if (definition.name !== "Settings") continue;
    for (const metadata of SCHEMA_METADATA_ROWS) {
      const desired: SheetRecord = { ...metadata };
      const existing = sheet?.getRowByPrimaryKey(
        definition.primaryKey,
        metadata.settingKey,
      );
      if (existing && recordMatches(existing, desired)) continue;
      actions.push({
        type: "UPSERT_SCHEMA_METADATA",
        sheet: "Settings",
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
