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
  setValues(values: unknown[][]): GasRange;
}

interface GasSheet {
  appendRow(values: unknown[]): GasSheet;
  getLastColumn(): number;
  getLastRow(): number;
  getRange(
    row: number,
    column: number,
    rows: number,
    columns: number,
  ): GasRange;
}

interface GasSpreadsheet {
  getSheetByName(name: string): GasSheet | null;
  insertSheet(name: string): GasSheet;
}

declare const SpreadsheetApp: {
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
