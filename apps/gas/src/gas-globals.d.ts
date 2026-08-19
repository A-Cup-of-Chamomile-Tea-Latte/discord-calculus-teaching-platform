interface GasTextOutput {
  setMimeType(mimeType: string): GasTextOutput;
}

interface GasHtmlOutput {
  setTitle(title: string): GasHtmlOutput;
}

interface GasScriptProperties {
  getProperty(key: string): string | null;
  setProperty(key: string, value: string): GasScriptProperties;
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
  createFilter(): unknown;
  getValues(): unknown[][];
  setBackground(color: string): GasRange;
  setFontColor(color: string): GasRange;
  setFontWeight(weight: string): GasRange;
  setHorizontalAlignment(alignment: string): GasRange;
  setValues(values: unknown[][]): GasRange;
  setWrap(wrap: boolean): GasRange;
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
  getFilter(): unknown | null;
  hideSheet(): GasSheet;
  isSheetHidden(): boolean;
  setFrozenRows(rows: number): GasSheet;
  setColumnWidth(column: number, width: number): GasSheet;
  setRowHeight(row: number, height: number): GasSheet;
  showSheet(): GasSheet;
}

interface GasSpreadsheet {
  deleteSheet(sheet: GasSheet): void;
  getSheetByName(name: string): GasSheet | null;
  getSheets(): GasSheet[];
  insertSheet(name: string): GasSheet;
  getId(): string;
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
  showSidebar(output: GasHtmlOutput): void;
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
  formatDate(date: Date, timeZone: string, format: string): string;
};

interface GasTriggerBuilder {
  timeBased(): GasTriggerBuilder;
  everyMinutes(minutes: number): GasTriggerBuilder;
  create(): unknown;
}

interface GasTrigger {
  getHandlerFunction(): string;
}

declare const ScriptApp: {
  newTrigger(handler: string): GasTriggerBuilder;
  getProjectTriggers(): GasTrigger[];
  deleteTrigger(trigger: GasTrigger): void;
};

declare const MailApp: {
  sendEmail(recipient: string, subject: string, body: string): void;
};
