import { loadRuntimeConfig } from "../config";
import type { SheetPort, SheetRecord, WorkbookPort } from "./bootstrap";
import {
  bootstrapWorkbook,
  migrateToCompactWorkbook,
  type BootstrapResult,
  type CompactMigrationResult,
} from "./bootstrap";
import { SHEET_SCHEMAS } from "./schema";

class GasSheetAdapter implements SheetPort {
  constructor(private readonly sheet: GasSheet) {}

  getHeaders(): string[] {
    const lastColumn = this.sheet.getLastColumn();
    if (lastColumn === 0) return [];
    return (this.sheet.getRange(1, 1, 1, lastColumn).getValues()[0] ?? []).map(
      (value) => String(value),
    );
  }

  getDataRowCount(): number {
    return Math.max(0, this.sheet.getLastRow() - 1);
  }

  getColumnValues(header: string): string[] {
    const headers = this.getHeaders();
    const columnIndex = headers.indexOf(header);
    const rowCount = this.getDataRowCount();
    if (columnIndex < 0 || rowCount === 0) return [];
    return this.sheet
      .getRange(2, columnIndex + 1, rowCount, 1)
      .getValues()
      .map((row) => String(row[0] ?? ""));
  }

  appendHeaders(headers: readonly string[]): void {
    if (headers.length === 0) return;
    const startColumn = this.sheet.getLastColumn() + 1;
    this.sheet
      .getRange(1, startColumn, 1, headers.length)
      .setValues([[...headers]]);
  }

  getRowByPrimaryKey(primaryKey: string, value: string): SheetRecord | null {
    const headers = this.getHeaders();
    const keyIndex = headers.indexOf(primaryKey);
    if (keyIndex < 0 || this.sheet.getLastRow() < 2) return null;
    const rows = this.sheet
      .getRange(2, 1, this.sheet.getLastRow() - 1, headers.length)
      .getValues();
    const row = rows.find((candidate) => String(candidate[keyIndex]) === value);
    if (!row) return null;
    return Object.fromEntries(
      headers.map((header, index) => [
        header,
        (row[index] ?? null) as string | number | boolean | null,
      ]),
    );
  }

  upsertRowByPrimaryKey(
    primaryKey: string,
    value: string,
    record: SheetRecord,
  ): "inserted" | "updated" | "unchanged" {
    const headers = this.getHeaders();
    const existing = this.getRowByPrimaryKey(primaryKey, value);
    if (
      existing &&
      Object.entries(record).every(([key, cell]) => existing[key] === cell)
    ) {
      return "unchanged";
    }
    const output = headers.map(
      (header) => record[header] ?? existing?.[header] ?? "",
    );
    if (!existing) {
      this.sheet.appendRow(output);
      return "inserted";
    }
    const keyIndex = headers.indexOf(primaryKey);
    const rows = this.sheet
      .getRange(2, 1, this.sheet.getLastRow() - 1, headers.length)
      .getValues();
    const offset = rows.findIndex((row) => String(row[keyIndex]) === value);
    this.sheet.getRange(offset + 2, 1, 1, headers.length).setValues([output]);
    return "updated";
  }
}

class GasWorkbookAdapter implements WorkbookPort {
  constructor(private readonly spreadsheet: GasSpreadsheet) {}

  getSheet(name: string): SheetPort | null {
    const sheet = this.spreadsheet.getSheetByName(name);
    return sheet ? new GasSheetAdapter(sheet) : null;
  }

  createSheet(name: string): SheetPort {
    return new GasSheetAdapter(this.spreadsheet.insertSheet(name));
  }

  deleteSheet(name: string): void {
    const sheet = this.spreadsheet.getSheetByName(name);
    if (sheet) this.spreadsheet.deleteSheet(sheet);
  }

  listSheetNames(): string[] {
    return this.spreadsheet.getSheets().map((sheet) => sheet.getName());
  }
}

function configureCompactPresentation(spreadsheet: GasSpreadsheet): void {
  for (const definition of SHEET_SCHEMAS) {
    const sheet = spreadsheet.getSheetByName(definition.name);
    if (!sheet) continue;
    const columnCount = sheet.getLastColumn();
    if (columnCount > 0) {
      sheet
        .getRange(1, 1, 1, columnCount)
        .setFontWeight("bold")
        .setBackground("#f1f3f4");
      sheet.setFrozenRows(1);
      sheet.autoResizeColumns(1, columnCount);
    }
    if (definition.audience === "MACHINE" && !sheet.isSheetHidden()) {
      sheet.hideSheet();
    }
    if (definition.audience === "HUMAN" && sheet.isSheetHidden()) {
      sheet.showSheet();
    }
  }
}

export function bootstrapRuntimeSpreadsheet(dryRun = true): BootstrapResult {
  const config = loadRuntimeConfig();
  if (config.fixtureMode) {
    throw new Error("Cloud spreadsheet bootstrap is disabled in fixture mode");
  }
  if (!config.spreadsheetId) throw new Error("SPREADSHEET_ID is required");
  return bootstrapSpreadsheet(
    SpreadsheetApp.openById(config.spreadsheetId),
    dryRun,
  );
}

export function bootstrapActiveSpreadsheet(dryRun = true): BootstrapResult {
  return bootstrapSpreadsheet(SpreadsheetApp.getActiveSpreadsheet(), dryRun);
}

export function migrateActiveSpreadsheet(
  dryRun = true,
): CompactMigrationResult {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const result = migrateToCompactWorkbook(new GasWorkbookAdapter(spreadsheet), {
    dryRun,
  });
  if (!dryRun && result.blockers.length === 0)
    configureCompactPresentation(spreadsheet);
  return result;
}

function bootstrapSpreadsheet(
  spreadsheet: GasSpreadsheet,
  dryRun: boolean,
): BootstrapResult {
  return bootstrapWorkbook(new GasWorkbookAdapter(spreadsheet), { dryRun });
}
