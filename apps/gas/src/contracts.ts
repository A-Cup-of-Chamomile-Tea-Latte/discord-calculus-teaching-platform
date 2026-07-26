export type HttpMethod = "GET" | "POST";

export interface GasRequest {
  method: HttpMethod;
  path: string;
  query: Record<string, string>;
  rawBody: string;
}

export interface JsonRouteResponse {
  kind: "json";
  status: number;
  body: Record<string, unknown>;
}

export interface HtmlRouteResponse {
  kind: "html";
  status: number;
  title: string;
  body: string;
}

export type RouteResponse = JsonRouteResponse | HtmlRouteResponse;

export interface AppConfig {
  environment: string;
  fixtureMode: boolean;
  spreadsheetId: string | null;
}

export interface ScriptPropertyReader {
  getProperty(key: string): string | null;
}

export interface DoGetEvent {
  parameter?: Record<string, string>;
  pathInfo?: string | null;
}

export interface DoPostEvent extends DoGetEvent {
  postData?: { contents?: string };
}
