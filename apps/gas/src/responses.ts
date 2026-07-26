import type { RouteResponse } from "./contracts";

export function toGasOutput(
  response: RouteResponse,
): GasTextOutput | GasHtmlOutput {
  if (response.kind === "html") {
    return HtmlService.createHtmlOutput(response.body).setTitle(response.title);
  }
  return ContentService.createTextOutput(
    JSON.stringify({ status: response.status, ...response.body }),
  ).setMimeType(ContentService.MimeType.JSON);
}
