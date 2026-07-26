import type {
  SheetCell,
  SheetPort,
  SheetRecord,
  WorkbookPort,
} from "./bootstrap";

export interface InMemorySheetSeed {
  headers?: string[];
  rows?: SheetRecord[];
}

export class InMemorySheet implements SheetPort {
  readonly headers: string[];
  readonly rows: SheetRecord[];

  constructor(seed: InMemorySheetSeed = {}) {
    this.headers = [...(seed.headers ?? [])];
    this.rows = (seed.rows ?? []).map((row) => ({ ...row }));
  }

  getHeaders(): string[] {
    return [...this.headers];
  }

  appendHeaders(headers: readonly string[]): void {
    for (const header of headers) {
      if (!this.headers.includes(header)) this.headers.push(header);
    }
  }

  getRowByPrimaryKey(primaryKey: string, value: string): SheetRecord | null {
    const row = this.rows.find((candidate) => candidate[primaryKey] === value);
    return row ? { ...row } : null;
  }

  upsertRowByPrimaryKey(
    primaryKey: string,
    value: string,
    record: SheetRecord,
  ): "inserted" | "updated" | "unchanged" {
    const index = this.rows.findIndex(
      (candidate) => candidate[primaryKey] === value,
    );
    if (index < 0) {
      this.rows.push({ ...record });
      return "inserted";
    }
    const current = this.rows[index] ?? {};
    const changed = Object.entries(record).some(
      ([key, cell]) => current[key] !== cell,
    );
    if (!changed) return "unchanged";
    this.rows[index] = { ...current, ...record };
    return "updated";
  }

  appendFixtureRow(record: Record<string, SheetCell>): void {
    this.rows.push({ ...record });
  }
}

export class InMemoryWorkbook implements WorkbookPort {
  readonly sheets = new Map<string, InMemorySheet>();

  constructor(seed: Record<string, InMemorySheetSeed> = {}) {
    for (const [name, sheetSeed] of Object.entries(seed)) {
      this.sheets.set(name, new InMemorySheet(sheetSeed));
    }
  }

  getSheet(name: string): InMemorySheet | null {
    return this.sheets.get(name) ?? null;
  }

  createSheet(name: string): InMemorySheet {
    const existing = this.sheets.get(name);
    if (existing) return existing;
    const sheet = new InMemorySheet();
    this.sheets.set(name, sheet);
    return sheet;
  }
}
