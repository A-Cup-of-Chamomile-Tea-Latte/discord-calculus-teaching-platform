import type { AppConfig, ScriptPropertyReader } from "./contracts";

export const scriptPropertyKeys = {
  environment: "APP_ENVIRONMENT",
  fixtureMode: "FIXTURE_MODE",
  spreadsheetId: "SPREADSHEET_ID",
} as const;

function optionalTrimmed(value: string | null): string | null {
  const normalized = value?.trim() ?? "";
  return normalized || null;
}

export function loadConfig(reader: ScriptPropertyReader): AppConfig {
  const fixtureValue = optionalTrimmed(
    reader.getProperty(scriptPropertyKeys.fixtureMode),
  );
  const fixtureMode = fixtureValue === null ? true : fixtureValue === "true";
  if (fixtureValue !== null && !/^(true|false)$/.test(fixtureValue)) {
    throw new Error("FIXTURE_MODE must be exactly true or false");
  }

  const config: AppConfig = {
    environment:
      optionalTrimmed(reader.getProperty(scriptPropertyKeys.environment)) ??
      "fixture",
    fixtureMode,
    spreadsheetId: optionalTrimmed(
      reader.getProperty(scriptPropertyKeys.spreadsheetId),
    ),
  };

  if (!config.fixtureMode && config.spreadsheetId === null) {
    throw new Error("SPREADSHEET_ID is required when fixture mode is disabled");
  }
  return config;
}

export function loadRuntimeConfig(): AppConfig {
  return loadConfig(PropertiesService.getScriptProperties());
}
