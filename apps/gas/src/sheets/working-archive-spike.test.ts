import { describe, expect, it } from "vitest";

import {
  CellQuotaEstimator,
  FixtureWorkingArchiveStore,
  simulateTriggerSchedule,
  type ChangedCaseFixture,
} from "./working-archive-spike";

const OPEN: ChangedCaseFixture = {
  caseId: "case_open_001",
  changeVersion: 1,
  status: "OPEN",
  projection: { title: "fixture limit question" },
  updatedAt: "2026-07-23T08:00:00+08:00",
};
const CLOSED: ChangedCaseFixture = {
  caseId: "case_closed_001",
  changeVersion: 2,
  status: "CLOSED",
  projection: { title: "fixture derivative question" },
  updatedAt: "2026-07-23T08:05:00+08:00",
};

describe("fixture working/archive spike", () => {
  it("batches changed cases, estimates quota, caches projection, and is idempotent", () => {
    const store = new FixtureWorkingArchiveStore();
    const first = store.writeChangedCaseBatch([OPEN, CLOSED], {
      batchSize: 1,
      quota: new CellQuotaEstimator(),
    });
    const replay = store.writeChangedCaseBatch([OPEN], {
      batchSize: 10,
      quota: new CellQuotaEstimator(),
    });
    expect(first).toEqual({
      inserted: 2,
      skippedAsDuplicate: 0,
      batches: 2,
      estimatedWrites: 12,
    });
    expect(replay.skippedAsDuplicate).toBe(1);
    expect(store.queryActiveCaseCached(OPEN.caseId, 100)?.projection).toEqual(
      OPEN.projection,
    );
  });

  it("plans and applies fixture-only weekly rollover once", () => {
    const store = new FixtureWorkingArchiveStore();
    store.writeChangedCaseBatch([OPEN, CLOSED], {
      batchSize: 25,
      quota: new CellQuotaEstimator(),
    });
    const plan = store.planWeeklyMaintenance("weekly_run_001", "2026-W30");
    expect(plan.dryRun).toBe(true);
    expect(plan.period).toBe("2026-W30");
    expect(plan.closedCaseIds).toEqual([CLOSED.caseId]);
    expect(
      store.applyFixtureRollover(plan, "2026-07-26T02:00:00+08:00"),
    ).toEqual({
      rolledOver: 1,
      duplicate: false,
    });
    expect(
      store.applyFixtureRollover(plan, "2026-07-26T02:00:00+08:00").duplicate,
    ).toBe(true);
    expect(store.activeCases.has(OPEN.caseId)).toBe(true);
    expect(store.activeCases.has(CLOSED.caseId)).toBe(false);
    expect(store.archiveIndex.size).toBe(1);
  });

  it("defensively copies nested state and reports actual rollover count", () => {
    const store = new FixtureWorkingArchiveStore();
    const nested = { ...OPEN, projection: { nested: { value: 1 } } };
    store.writeChangedCaseBatch([nested, CLOSED], {
      batchSize: 10,
      quota: new CellQuotaEstimator(),
    });
    const first = store.queryActiveCaseCached(OPEN.caseId, 100);
    expect(first).not.toBeNull();
    (first!.projection.nested as { value: number }).value = 99;
    expect(store.queryActiveCaseCached(OPEN.caseId, 101)?.projection).toEqual({
      nested: { value: 1 },
    });
    const plan = store.planWeeklyMaintenance("weekly_run_partial", "2026-W30");
    store.activeCases.delete(CLOSED.caseId);
    expect(
      store.applyFixtureRollover(plan, "2026-07-26T02:00:00+08:00").rolledOver,
    ).toBe(0);
  });

  it("simulates bounded schedules without registering a trigger", () => {
    expect(simulateTriggerSchedule(1_000, 15, 3)).toEqual([
      1_000, 901_000, 1_801_000,
    ]);
    expect(() => simulateTriggerSchedule(0, 0, 1)).toThrow();
  });
});
