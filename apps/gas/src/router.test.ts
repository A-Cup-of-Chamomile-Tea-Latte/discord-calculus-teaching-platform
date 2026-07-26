import { describe, expect, it } from "vitest";

import type { AppConfig, GasRequest } from "./contracts";
import { normalizePath, routeRequest } from "./router";

const fixtureConfig: AppConfig = {
  environment: "test",
  fixtureMode: true,
  spreadsheetId: null,
};

function request(overrides: Partial<GasRequest> = {}): GasRequest {
  return {
    method: "GET",
    path: "/",
    query: {},
    rawBody: "",
    ...overrides,
  };
}

describe("GAS pure router", () => {
  it("normalizes paths and serves an HTML fixture landing page", () => {
    expect(normalizePath(" //health/ ")).toBe("/health");
    expect(routeRequest(request(), fixtureConfig)).toMatchObject({
      kind: "html",
      status: 200,
    });
  });

  it("reports health without claiming to host the Discord Gateway", () => {
    expect(
      routeRequest(request({ path: "/health" }), fixtureConfig),
    ).toMatchObject({
      kind: "json",
      status: 200,
      body: { ok: true, fixtureMode: true, discordGatewayHost: false },
    });
  });

  it("accepts object metadata on the fixture-only POST route without persistence", () => {
    expect(
      routeRequest(
        request({
          method: "POST",
          path: "/api/fixture/echo",
          rawBody: JSON.stringify({ beta: "not echoed", alpha: 1 }),
        }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 200,
      body: {
        fixture: true,
        persisted: false,
        receivedKeys: ["alpha", "beta"],
      },
    });
  });

  it("rejects malformed JSON and disables fixture routes outside fixture mode", () => {
    expect(
      routeRequest(
        request({
          method: "POST",
          path: "/api/fixture/echo",
          rawBody: "not-json",
        }),
        fixtureConfig,
      ),
    ).toMatchObject({ status: 400 });
    expect(
      routeRequest(request({ method: "POST", path: "/api/fixture/echo" }), {
        ...fixtureConfig,
        fixtureMode: false,
        spreadsheetId: "configured",
      }),
    ).toMatchObject({ status: 403 });
  });

  it("returns a structured 404", () => {
    expect(
      routeRequest(
        request({ method: "POST", path: "/missing/" }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 404,
      body: { error: "ROUTE_NOT_FOUND", method: "POST", path: "/missing" },
    });
  });

  it("validates missing and malformed public case lookup input", () => {
    expect(
      routeRequest(request({ path: "/api/cases/lookup" }), fixtureConfig),
    ).toMatchObject({ status: 400, body: { outcome: "INVALID" } });
    expect(
      routeRequest(
        request({ path: "/api/cases/lookup", query: { case: "421" } }),
        fixtureConfig,
      ),
    ).toMatchObject({ status: 400, body: { outcome: "INVALID" } });
  });

  it("serves a public lookup and excludes Private Support", () => {
    expect(
      routeRequest(
        request({
          path: "/api/cases/lookup",
          query: { case: "C01-7K4M2Q-0702-1000" },
        }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 200,
      body: { outcome: "FOUND", case: { caseNumber: "C01-7K4M2Q-0702-1000" } },
    });
    expect(
      routeRequest(
        request({
          path: "/api/cases/lookup",
          query: { case: "C99-B4W9K6-0702-1500-P" },
        }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 404,
      body: { outcome: "NOT_FOUND", case: null },
    });
  });

  it("provides explicit refresh and a disabled follow-up provider", () => {
    expect(
      routeRequest(
        request({
          method: "POST",
          path: "/api/cases/refresh",
          rawBody: JSON.stringify({ caseNumber: "C01-7K4M2Q-0702-1000" }),
        }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 200,
      body: { polling: false, outcome: "NO_OP" },
    });
    expect(
      routeRequest(
        request({
          method: "POST",
          path: "/api/cases/follow-up",
          rawBody: JSON.stringify({
            caseNumber: "C01-7K4M2Q-0702-1000",
            content: "Fictional follow-up content",
            authorDisplayMode: "ANONYMOUS",
          }),
        }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 501,
      body: {
        accepted: false,
        persisted: false,
        outcome: "NOT_CONFIGURED",
      },
    });
    expect(
      routeRequest(
        request({
          method: "POST",
          path: "/api/cases/follow-up",
          rawBody: JSON.stringify({
            caseNumber: "C01-7K4M2Q-0702-1000",
            content: "x",
            authorDisplayMode: "ANONYMOUS",
          }),
        }),
        fixtureConfig,
      ),
    ).toMatchObject({
      status: 400,
      body: { error: "INVALID_FOLLOW_UP_CONTENT", accepted: false },
    });
  });

  it("does not fall back to fixture data when production providers are absent", () => {
    expect(
      routeRequest(request({ path: "/api/cases" }), {
        ...fixtureConfig,
        fixtureMode: false,
        spreadsheetId: "configured",
      }),
    ).toMatchObject({
      status: 503,
      body: { error: "CASE_PROVIDER_NOT_CONFIGURED" },
    });
  });
});
