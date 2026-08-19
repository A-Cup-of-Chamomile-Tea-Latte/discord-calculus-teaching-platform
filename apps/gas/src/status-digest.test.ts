import { describe, expect, it } from "vitest";

import { bootstrapWorkbook } from "./sheets/bootstrap";
import { InMemoryWorkbook } from "./sheets/in-memory-workbook";
import { classifyStatus, digestBody } from "./status-digest";

function workbook(heartbeat: string, status = "HEALTHY"): InMemoryWorkbook {
  const result = new InMemoryWorkbook();
  bootstrapWorkbook(result, { dryRun: false });
  result.getSheet("Operations")?.appendFixtureRow({
    schemaVersion: "2.0.0",
    operationKey: "data-bridge",
    service: "calculus-data-bridge",
    component: "apps-script-api",
    status,
    mode: "PRODUCTION",
    lastHeartbeatAt: heartbeat,
    checkedAt: heartbeat,
  });
  return result;
}

describe("status digest watchdog", () => {
  const now = new Date("2026-08-19T12:00:00Z");

  it("classifies fresh, stale and critical receipts", () => {
    expect(classifyStatus(workbook("2026-08-19T11:55:00Z"), now).level).toBe(
      "NORMAL",
    );
    expect(classifyStatus(workbook("2026-08-19T11:40:00Z"), now).level).toBe(
      "ATTENTION",
    );
    expect(classifyStatus(workbook("2026-08-19T11:20:00Z"), now).level).toBe(
      "CRITICAL",
    );
    expect(
      classifyStatus(workbook("2026-08-19T11:59:00Z", "OAUTH_REVOKED"), now)
        .level,
    ).toBe("CRITICAL");
  });

  it("keeps the message short and free of process details", () => {
    const body = digestBody(
      classifyStatus(workbook("2026-08-19T11:55:00Z"), now),
    );
    expect(body).toContain("整體狀態：正常");
    expect(body).not.toContain("PID");
    expect(body).not.toContain("memory");
    expect(body.split("\n").length).toBeLessThanOrEqual(14);
  });
});
