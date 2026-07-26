import { loadRuntimeConfig } from "./config";
import type {
  DoGetEvent,
  DoPostEvent,
  GasRequest,
  HttpMethod,
} from "./contracts";
import { toGasOutput } from "./responses";
import { routeRequest } from "./router";
import { bootstrapRuntimeSpreadsheet } from "./sheets/gas-workbook";

function eventToRequest(
  method: HttpMethod,
  event: DoGetEvent | DoPostEvent | undefined,
): GasRequest {
  const postEvent = event as DoPostEvent | undefined;
  return {
    method,
    path: event?.pathInfo ?? "/",
    query: event?.parameter ?? {},
    rawBody: postEvent?.postData?.contents ?? "",
  };
}

function handle(
  method: HttpMethod,
  event: DoGetEvent | DoPostEvent | undefined,
): GasTextOutput | GasHtmlOutput {
  try {
    const response = routeRequest(
      eventToRequest(method, event),
      loadRuntimeConfig(),
    );
    return toGasOutput(response);
  } catch {
    return toGasOutput({
      kind: "json",
      status: 500,
      body: { ok: false, error: "CONFIGURATION_OR_RUNTIME_ERROR" },
    });
  }
}

export function doGet(event?: DoGetEvent): GasTextOutput | GasHtmlOutput {
  return handle("GET", event);
}

export function doPost(event?: DoPostEvent): GasTextOutput | GasHtmlOutput {
  return handle("POST", event);
}

export function bootstrapSheetsDryRun(): unknown {
  return bootstrapRuntimeSpreadsheet(true);
}

export function bootstrapSheetsApply(): unknown {
  return bootstrapRuntimeSpreadsheet(false);
}
