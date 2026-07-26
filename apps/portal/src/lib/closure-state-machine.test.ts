import { describe, expect, it } from "vitest";

import {
  applyAutomaticClosure,
  manualClose,
  recordNewActivity,
  type ClosureState,
} from "./closure-state-machine";

const answered: ClosureState = {
  status: "ANSWERED",
  lastUpdateAt: "2026-07-01T00:00:00Z",
  lastReadAt: "2026-07-01T01:00:00Z",
  closureSource: null,
  closedAt: null,
  reopenedAt: null,
};

describe("closure state machine", () => {
  it("manually closes with a MANUAL source and timestamp", () => {
    expect(manualClose(answered, "2026-07-02T00:00:00Z")).toMatchObject({
      status: "CLOSED",
      closureSource: "MANUAL",
      closedAt: "2026-07-02T00:00:00Z",
    });
  });

  it("temporarily auto-closes after the configurable threshold and verified view", () => {
    const state = applyAutomaticClosure(answered, "2026-07-04T00:00:00Z", {
      temporaryCloseAfterDays: 3,
      automaticCloseAfterDays: 7,
    });
    expect(state).toMatchObject({
      status: "TEMPORARILY_CLOSED",
      closureSource: "AUTO",
    });
  });

  it("does not infer read evidence from inactivity", () => {
    expect(
      applyAutomaticClosure(
        { ...answered, lastReadAt: null },
        "2026-07-05T00:00:00Z",
      ),
    ).toEqual({ ...answered, lastReadAt: null });
  });

  it("automatically closes a temporary case after seven cumulative inactive days", () => {
    const temporary: ClosureState = {
      ...answered,
      status: "TEMPORARILY_CLOSED",
      closureSource: "AUTO",
      closedAt: "2026-07-04T00:00:00Z",
    };
    expect(
      applyAutomaticClosure(temporary, "2026-07-08T00:00:00Z"),
    ).toMatchObject({ status: "CLOSED", closureSource: "AUTO" });
  });

  it("reopens a manually or automatically closed case on new activity", () => {
    const closed = manualClose(answered, "2026-07-02T00:00:00Z");
    expect(recordNewActivity(closed, "2026-07-03T00:00:00Z")).toMatchObject({
      status: "REOPENED",
      closureSource: null,
      closedAt: null,
      reopenedAt: "2026-07-03T00:00:00Z",
    });
  });

  it("rejects inverted or hard-to-interpret policy thresholds", () => {
    expect(() =>
      applyAutomaticClosure(answered, "2026-07-08T00:00:00Z", {
        temporaryCloseAfterDays: 7,
        automaticCloseAfterDays: 3,
      }),
    ).toThrow("INVALID_CLOSURE_POLICY");
  });
});
