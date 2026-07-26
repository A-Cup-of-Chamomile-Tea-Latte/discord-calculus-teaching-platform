import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { build } from "esbuild";

const root = fileURLToPath(new URL("../", import.meta.url));
const outputDirectory = fileURLToPath(new URL("../dist/", import.meta.url));
const codeOutput = fileURLToPath(new URL("../dist/Code.js", import.meta.url));
const manifestSource = fileURLToPath(
  new URL("../appsscript.json", import.meta.url),
);
const manifestOutput = fileURLToPath(
  new URL("../dist/appsscript.json", import.meta.url),
);

mkdirSync(outputDirectory, { recursive: true });

await build({
  absWorkingDir: root,
  entryPoints: ["src/index.ts"],
  outfile: codeOutput,
  bundle: true,
  format: "iife",
  globalName: "CalculusGasApp",
  footer: {
    js: [
      "var doGet = CalculusGasApp.doGet;",
      "var doPost = CalculusGasApp.doPost;",
      "var bootstrapSheetsDryRun = CalculusGasApp.bootstrapSheetsDryRun;",
      "var bootstrapSheetsApply = CalculusGasApp.bootstrapSheetsApply;",
    ].join("\n"),
  },
  platform: "browser",
  target: ["es2019"],
  legalComments: "none",
  minify: false,
  sourcemap: false,
});

copyFileSync(manifestSource, manifestOutput);

const bundledCode = readFileSync(codeOutput, "utf8");
if (!bundledCode.includes("var doGet = CalculusGasApp.doGet")) {
  throw new Error("Apps Script bundle does not expose doGet");
}
if (!bundledCode.includes("var doPost = CalculusGasApp.doPost")) {
  throw new Error("Apps Script bundle does not expose doPost");
}
if (!bundledCode.includes("var bootstrapSheetsDryRun")) {
  throw new Error(
    "Apps Script bundle does not expose Sheets dry-run bootstrap",
  );
}
if (!bundledCode.includes("var bootstrapSheetsApply")) {
  throw new Error("Apps Script bundle does not expose Sheets apply bootstrap");
}
if (/REPLACE_WITH_SCRIPT_ID|scriptId/.test(bundledCode)) {
  throw new Error(
    "Apps Script bundle unexpectedly contains clasp project state",
  );
}

console.log("GAS bundle built: dist/Code.js + dist/appsscript.json");
