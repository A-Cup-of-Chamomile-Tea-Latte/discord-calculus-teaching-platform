import type {
  AppConfig,
  GasRequest,
  JsonRouteResponse,
  RouteResponse,
} from "./contracts";
import type { FollowUpRequest } from "./cases/contracts";
import { fixtureCaseService } from "./cases/fixture-service";
import type { CaseService } from "./cases/service";

function json(
  status: number,
  body: Record<string, unknown>,
): JsonRouteResponse {
  return { kind: "json", status, body };
}

function parseObjectBody(rawBody: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(rawBody);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function normalizePath(path: string): string {
  const withoutQuery = path.trim().split("?", 1)[0] ?? "";
  const normalized = `/${withoutQuery.replace(/^\/+|\/+$/g, "")}`;
  return normalized === "/" ? "/" : normalized;
}

export function routeRequest(
  request: GasRequest,
  config: AppConfig,
  caseService: CaseService = fixtureCaseService,
): RouteResponse {
  const path = normalizePath(request.path);

  if (request.method === "GET" && path === "/") {
    return {
      kind: "html",
      status: 200,
      title: "Calculus GAS fixture scaffold",
      body: `<main><h1>Calculus GAS fixture scaffold</h1><p>Mode: ${
        config.fixtureMode ? "fixture" : "configured"
      }</p><p>This web app is an administrative/API surface. It is not a Discord Gateway host.</p></main>`,
    };
  }

  if (request.method === "GET" && path === "/health") {
    return json(200, {
      ok: true,
      service: "calculus-gas",
      environment: config.environment,
      fixtureMode: config.fixtureMode,
      discordGatewayHost: false,
    });
  }

  if (request.method === "POST" && path === "/api/fixture/echo") {
    if (!config.fixtureMode) {
      return json(403, {
        ok: false,
        error: "FIXTURE_ROUTE_DISABLED",
      });
    }
    const payload = parseObjectBody(request.rawBody);
    if (!payload) {
      return json(400, { ok: false, error: "INVALID_JSON_OBJECT" });
    }
    return json(200, {
      ok: true,
      fixture: true,
      receivedKeys: Object.keys(payload).sort(),
      persisted: false,
    });
  }

  if (path.startsWith("/api/cases") && !config.fixtureMode) {
    return json(503, {
      ok: false,
      error: "CASE_PROVIDER_NOT_CONFIGURED",
    });
  }

  if (request.method === "GET" && path === "/api/cases/lookup") {
    const response = caseService.lookup(request.query.case ?? "");
    const status =
      response.outcome === "FOUND"
        ? 200
        : response.outcome === "INVALID"
          ? 400
          : response.outcome === "NOT_PUBLIC"
            ? 403
            : 404;
    return json(status, { ...response });
  }

  if (request.method === "GET" && path === "/api/cases") {
    return json(200, {
      schemaVersion: "1.0",
      cases: caseService.listPublic(),
      polling: false,
    });
  }

  if (request.method === "POST" && path === "/api/cases/refresh") {
    const payload = parseObjectBody(request.rawBody);
    if (!payload || typeof payload.caseNumber !== "string") {
      return json(400, { ok: false, error: "CASE_NUMBER_REQUIRED" });
    }
    const result = caseService.requestRefresh(payload.caseNumber);
    const lookup = result.lookup as { outcome?: string } | undefined;
    const status =
      result.ok === true ? 200 : lookup?.outcome === "NOT_FOUND" ? 404 : 400;
    return json(status, result);
  }

  if (request.method === "POST" && path === "/api/cases/follow-up") {
    const payload = parseObjectBody(request.rawBody);
    const authorDisplayModes = ["REAL_NAME", "COURSE_ALIAS", "ANONYMOUS"];
    if (
      !payload ||
      typeof payload.caseNumber !== "string" ||
      typeof payload.content !== "string" ||
      typeof payload.authorDisplayMode !== "string" ||
      !authorDisplayModes.includes(payload.authorDisplayMode)
    ) {
      return json(400, { ok: false, error: "INVALID_FOLLOW_UP_REQUEST" });
    }
    const result = caseService.submitFollowUp(
      payload as unknown as FollowUpRequest,
    );
    const lookup = result.lookup as { outcome?: string } | undefined;
    const status =
      result.outcome === "NOT_CONFIGURED"
        ? 501
        : result.error
          ? 400
          : lookup?.outcome === "NOT_FOUND"
            ? 404
            : 200;
    return json(status, result);
  }

  return json(404, {
    ok: false,
    error: "ROUTE_NOT_FOUND",
    method: request.method,
    path,
  });
}
