import { describe, expect, it } from "vitest";

import {
  applyAutomaticClosure,
  manualClose,
  recordNewActivity,
  type ClosureState,
} from "./closure-state-machine";

const tracked: ClosureState = {
  status: "TRACKED",
  lastActivityAt: "2026-08-20T00:00:00Z",
  lastTeachingResponseAt: "2026-08-20T00:00:00Z",
  idleAt: null,
  closureSource: null,
  closedAt: null,
  reopenedAt: null,
};

describe("closure state machine", () => {
  it("manually closes with a MANUAL source and timestamp", () => {
    expect(
      manualClose(tracked, "2026-08-21T00:00:00Z", {
        isResponsibleStaff: true,
      }),
    ).toMatchObject({
      status: "CLOSED",
      closureSource: "MANUAL",
      closedAt: "2026-08-21T00:00:00Z",
    });
    expect(() =>
      manualClose(tracked, "2026-08-21T00:00:00Z", {
        isResponsibleStaff: false,
      }),
    ).toThrow("MANUAL_CLOSE_NOT_ALLOWED");
  });

  it("moves Tracked to Idle after 48 hours without a learner reply", () => {
    const state = applyAutomaticClosure(tracked, "2026-08-22T00:00:00Z");
    expect(state).toMatchObject({
      status: "IDLE",
      idleAt: "2026-08-22T00:00:00Z",
      closureSource: null,
    });
  });

  it("does not start the timer without a teaching-team response", () => {
    expect(
      applyAutomaticClosure(
        { ...tracked, lastTeachingResponseAt: null },
        "2026-08-24T00:00:00Z",
      ),
    ).toEqual({ ...tracked, lastTeachingResponseAt: null });
  });

  it("moves Idle to Auto Closed after another 48 hours", () => {
    const idle: ClosureState = {
      ...tracked,
      status: "IDLE",
      idleAt: "2026-08-22T00:00:00Z",
    };
    expect(applyAutomaticClosure(idle, "2026-08-24T00:00:00Z")).toMatchObject({
      status: "AUTO_CLOSED",
      closureSource: "AUTO",
    });
  });

  it("returns Idle and closed cases to Tracked on new activity", () => {
    const closed = manualClose(tracked, "2026-08-21T00:00:00Z", {
      isResponsibleStaff: true,
    });
    expect(recordNewActivity(closed, "2026-08-22T00:00:00Z")).toMatchObject({
      status: "TRACKED",
      closureSource: null,
      closedAt: null,
      reopenedAt: "2026-08-22T00:00:00Z",
    });
    expect(
      recordNewActivity(
        { ...tracked, status: "IDLE", idleAt: "2026-08-22T00:00:00Z" },
        "2026-08-22T01:00:00Z",
      ),
    ).toMatchObject({ status: "TRACKED", idleAt: null, reopenedAt: null });
  });

  it("rejects non-positive policy thresholds", () => {
    expect(() =>
      applyAutomaticClosure(tracked, "2026-08-22T00:00:00Z", {
        idleAfterHours: 48,
        autoCloseAfterIdleHours: 0,
      }),
    ).toThrow("INVALID_CLOSURE_POLICY");
  });
});
