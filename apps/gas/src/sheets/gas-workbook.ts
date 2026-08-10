import { loadRuntimeConfig } from "../config";
import type { SheetPort, SheetRecord, WorkbookPort } from "./bootstrap";
import { bootstrapWorkbook, type BootstrapResult } from "./bootstrap";

class GasSheetAdapter implements SheetPort {
  constructor(private readonly sheet: GasSheet) {}

  getHeaders(): string[] {
    const lastColumn = this.sheet.getLastColumn();
    if (lastColumn === 0) return [];
    return (this.sheet.getRange(1, 1, 1, lastColumn).getValues()[0] ?? []).map(
      (value) => String(value),
    );
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

function bootstrapSpreadsheet(
  spreadsheet: GasSpreadsheet,
  dryRun: boolean,
): BootstrapResult {
  return bootstrapWorkbook(new GasWorkbookAdapter(spreadsheet), { dryRun });
}
