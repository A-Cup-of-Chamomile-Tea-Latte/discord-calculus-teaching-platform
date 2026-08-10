interface GasTextOutput {
  setMimeType(mimeType: string): GasTextOutput;
}

interface GasHtmlOutput {
  setTitle(title: string): GasHtmlOutput;
}

interface GasScriptProperties {
  getProperty(key: string): string | null;
}

declare const ContentService: {
  createTextOutput(content: string): GasTextOutput;
  MimeType: { JSON: string };
};

declare const HtmlService: {
  createHtmlOutput(content: string): GasHtmlOutput;
};

declare const PropertiesService: {
  getScriptProperties(): GasScriptProperties;
};

interface GasRange {
  getValues(): unknown[][];
  setBackground(color: string): GasRange;
  setFontWeight(weight: string): GasRange;
  setValues(values: unknown[][]): GasRange;
}

interface GasSheet {
  appendRow(values: unknown[]): GasSheet;
  autoResizeColumns(startColumn: number, numberOfColumns: number): GasSheet;
  getLastColumn(): number;
  getLastRow(): number;
  getName(): string;
  getRange(
    row: number,
    column: number,
    rows: number,
    columns: number,
  ): GasRange;
  hideSheet(): GasSheet;
  isSheetHidden(): boolean;
  setFrozenRows(rows: number): GasSheet;
  showSheet(): GasSheet;
}

interface GasSpreadsheet {
  deleteSheet(sheet: GasSheet): void;
  getSheetByName(name: string): GasSheet | null;
  getSheets(): GasSheet[];
  insertSheet(name: string): GasSheet;
}

interface GasMenu {
  addItem(caption: string, functionName: string): GasMenu;
  addSeparator(): GasMenu;
  addToUi(): void;
}

interface GasUi {
  Button: { YES: unknown };
  ButtonSet: { OK: unknown; YES_NO: unknown };
  createMenu(caption: string): GasMenu;
  alert(title: string, prompt: string, buttons: unknown): unknown;
}

declare const SpreadsheetApp: {
  getActiveSpreadsheet(): GasSpreadsheet;
  getUi(): GasUi;
  openById(spreadsheetId: string): GasSpreadsheet;
};

interface GasScriptLock {
  tryLock(timeoutMilliseconds: number): boolean;
  releaseLock(): void;
}

declare const LockService: {
  getScriptLock(): GasScriptLock;
};

declare const Utilities: {
  computeDigest(algorithm: string, value: string, charset: string): number[];
  DigestAlgorithm: { SHA_256: string };
  Charset: { UTF_8: string };
};
