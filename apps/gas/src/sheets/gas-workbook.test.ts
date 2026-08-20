import { describe, expect, it } from "vitest";

import { GasSheetAdapter } from "./gas-workbook";

class FakeRange {
  constructor(
    private readonly sheet: FakeSheet,
    private readonly row: number,
    private readonly column: number,
    private readonly rowCount: number,
    private readonly columnCount: number,
  ) {}

  getValues(): unknown[][] {
    return Array.from({ length: this.rowCount }, (_, rowOffset) =>
      Array.from(
        { length: this.columnCount },
        (_, columnOffset) =>
          this.sheet.cells[this.row - 1 + rowOffset]?.[
            this.column - 1 + columnOffset
          ] ?? "",
      ),
    );
  }

  setValues(values: unknown[][]): FakeRange {
    values.forEach((sourceRow, rowOffset) => {
      const targetRow = this.row - 1 + rowOffset;
      this.sheet.cells[targetRow] ??= [];
      sourceRow.forEach((value, columnOffset) => {
        this.sheet.cells[targetRow]![this.column - 1 + columnOffset] = value;
      });
    });
    return this;
  }
}

class FakeSheet {
  constructor(readonly cells: unknown[][]) {}

  getLastColumn(): number {
    return this.cells[0]?.length ?? 0;
  }

  getLastRow(): number {
    return this.cells.length;
  }

  getRange(
    row: number,
    column: number,
    rowCount: number,
    columnCount: number,
  ): FakeRange {
    return new FakeRange(this, row, column, rowCount, columnCount);
  }

  appendRow(values: unknown[]): FakeSheet {
    this.cells.push([...values]);
    return this;
  }

  deleteRow(rowPosition: number): FakeSheet {
    this.cells.splice(rowPosition - 1, 1);
    return this;
  }
}

describe("GasSheetAdapter", () => {
  it("writes an explicit null instead of retaining an old claim value", () => {
    const sheet = new FakeSheet([
      ["jobRef", "status", "claimedBy", "leaseExpiresAt"],
      ["CMD-TST-v1", "CLAIMED", "worker#token", "2026-08-20T00:00:00Z"],
    ]);
    const adapter = new GasSheetAdapter(sheet as unknown as GasSheet);

    expect(
      adapter.upsertRowByPrimaryKey("jobRef", "CMD-TST-v1", {
        jobRef: "CMD-TST-v1",
        status: "COMPLETED",
        claimedBy: null,
        leaseExpiresAt: null,
      }),
    ).toBe("updated");
    expect(sheet.cells[1]).toEqual(["CMD-TST-v1", "COMPLETED", null, null]);
  });
});
