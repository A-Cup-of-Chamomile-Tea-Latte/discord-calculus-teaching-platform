import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { build } from "esbuild";

const root = fileURLToPath(new URL("../", import.meta.url));
const requestedTarget = process.argv[2];
const targets = requestedTarget ? [requestedTarget] : ["standalone", "bound"];

const definitions = {
  standalone: {
    entryPoint: "src/standalone.ts",
    manifest: "appsscript.json",
    wrappers: [
      { name: "doGet", parameters: "event", arguments: "event" },
      { name: "doPost", parameters: "event", arguments: "event" },
      { name: "bootstrapSheetsDryRun", parameters: "", arguments: "" },
      { name: "bootstrapSheetsApply", parameters: "", arguments: "" },
    ],
  },
  bound: {
    entryPoint: "src/bound.ts",
    manifest: "appsscript.bound.json",
    wrappers: [
      { name: "onOpen", parameters: "", arguments: "" },
      { name: "boundCompactDatabaseDryRun", parameters: "", arguments: "" },
      { name: "boundCompactDatabaseApply", parameters: "", arguments: "" },
    ],
  },
};

for (const target of targets) {
  const definition = definitions[target];
  if (!definition) throw new Error(`Unknown GAS build target: ${target}`);
  const outputDirectory = fileURLToPath(
    new URL(`../dist/${target}/`, import.meta.url),
  );
  const codeOutput = fileURLToPath(
    new URL(`../dist/${target}/Code.js`, import.meta.url),
  );
  const manifestSource = fileURLToPath(
    new URL(`../${definition.manifest}`, import.meta.url),
  );
  const manifestOutput = fileURLToPath(
    new URL(`../dist/${target}/appsscript.json`, import.meta.url),
  );

  mkdirSync(outputDirectory, { recursive: true });
  const globalName =
    target === "bound" ? "CalculusGasBound" : "CalculusGasStandalone";
  const footer = definition.wrappers
    .map(
      ({ name, parameters, arguments: callArguments }) =>
        `function ${name}(${parameters}) { return ${globalName}.${name}(${callArguments}); }`,
    )
    .join("\n");

  await build({
    absWorkingDir: root,
    entryPoints: [definition.entryPoint],
    outfile: codeOutput,
    bundle: true,
    format: "iife",
    globalName,
    footer: { js: footer },
    platform: "browser",
    target: ["es2019"],
    legalComments: "none",
    minify: false,
    sourcemap: false,
  });
  copyFileSync(manifestSource, manifestOutput);

  const bundledCode = readFileSync(codeOutput, "utf8");
  for (const { name, parameters } of definition.wrappers) {
    if (!bundledCode.includes(`function ${name}(${parameters})`)) {
      throw new Error(`${target} Apps Script bundle does not expose ${name}`);
    }
  }
  if (/REPLACE_WITH_SCRIPT_ID|scriptId/.test(bundledCode)) {
    throw new Error(
      `${target} bundle unexpectedly contains clasp project state`,
    );
  }
  console.log(
    `GAS ${target} bundle built: dist/${target}/Code.js + appsscript.json`,
  );
}
