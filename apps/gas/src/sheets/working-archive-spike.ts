/** Fixture-only working/archive behavior. No SpreadsheetApp or network adapter is used here. */

export interface ChangedCaseFixture {
  caseId: string;
  changeVersion: number;
  status:
    | "OPEN"
    | "WAITING_FOR_STUDENT"
    | "ANSWERED"
    | "ESCALATED"
    | "TEMPORARILY_CLOSED"
    | "CLOSED"
    | "REOPENED";
  projection: Record<string, unknown>;
  updatedAt: string;
}

export interface BatchWriteResult {
  inserted: number;
  skippedAsDuplicate: number;
  batches: number;
  estimatedWrites: number;
}

export interface ArchiveIndexFixture {
  archiveId: string;
  caseId: string;
  period: string;
  manifestId: string;
  archivedAt: string;
}

export interface WeeklyMaintenancePlan {
  runId: string;
  period: string;
  dryRun: true;
  closedCaseIds: string[];
  actions: readonly [
    "FLUSH_CHANGED_CASES",
    "REFRESH_PROJECTIONS",
    "ROLLOVER_CLOSED_CASES",
    "UPDATE_ARCHIVE_INDEX",
  ];
  estimatedWrites: number;
}

export interface QuotaEstimator {
  estimateWriteUnits(rowCount: number, columnsPerRow: number): number;
}

export class CellQuotaEstimator implements QuotaEstimator {
  estimateWriteUnits(rowCount: number, columnsPerRow: number): number {
    if (rowCount < 0 || columnsPerRow < 0)
      throw new Error("quota inputs must be non-negative");
    return rowCount * columnsPerRow;
  }
}

interface CacheEntry {
  expiresAt: number;
  value: ChangedCaseFixture;
}

function cloneProjection(
  value: Record<string, unknown>,
): Record<string, unknown> {
  const clone = (item: unknown): unknown => {
    if (item === null || ["string", "number", "boolean"].includes(typeof item))
      return item;
    if (Array.isArray(item)) return item.map(clone);
    if (typeof item === "object") {
      return Object.fromEntries(
        Object.entries(item).map(([key, child]) => [key, clone(child)]),
      );
    }
    throw new Error(
      "fixture projection must contain only JSON-compatible values",
    );
  };
  return clone(value) as Record<string, unknown>;
}

export class FixtureWorkingArchiveStore {
  readonly activeCases = new Map<string, ChangedCaseFixture>();
  readonly projections = new Map<string, Record<string, unknown>>();
  readonly archiveIndex = new Map<string, ArchiveIndexFixture>();
  readonly completedRuns = new Set<string>();
  private readonly changeKeys = new Set<string>();
  private readonly cache = new Map<string, CacheEntry>();

  writeChangedCaseBatch(
    changes: readonly ChangedCaseFixture[],
    options: { batchSize: number; quota: QuotaEstimator },
  ): BatchWriteResult {
    if (!Number.isInteger(options.batchSize) || options.batchSize < 1) {
      throw new Error("batchSize must be a positive integer");
    }
    let inserted = 0;
    let skippedAsDuplicate = 0;
    for (const change of changes) {
      const key = `${change.caseId}:${change.changeVersion}`;
      if (this.changeKeys.has(key)) {
        skippedAsDuplicate += 1;
        continue;
      }
      const current = this.activeCases.get(change.caseId);
      if (current && current.changeVersion > change.changeVersion) {
        throw new Error("out-of-order fixture change");
      }
      this.changeKeys.add(key);
      this.activeCases.set(change.caseId, {
        ...change,
        projection: cloneProjection(change.projection),
      });
      this.projections.set(change.caseId, cloneProjection(change.projection));
      this.cache.delete(change.caseId);
      inserted += 1;
    }
    return {
      inserted,
      skippedAsDuplicate,
      batches: inserted === 0 ? 0 : Math.ceil(inserted / options.batchSize),
      estimatedWrites: options.quota.estimateWriteUnits(inserted, 6),
    };
  }

  queryActiveCaseCached(
    caseId: string,
    nowMs: number,
    ttlMs = 60_000,
  ): ChangedCaseFixture | null {
    if (ttlMs < 0) throw new Error("ttlMs must be non-negative");
    const cached = this.cache.get(caseId);
    if (cached && cached.expiresAt >= nowMs)
      return {
        ...cached.value,
        projection: cloneProjection(cached.value.projection),
      };
    const value = this.activeCases.get(caseId);
    if (!value) return null;
    this.cache.set(caseId, {
      expiresAt: nowMs + ttlMs,
      value: { ...value, projection: cloneProjection(value.projection) },
    });
    return { ...value, projection: cloneProjection(value.projection) };
  }

  planWeeklyMaintenance(runId: string, period: string): WeeklyMaintenancePlan {
    const closedCaseIds = [...this.activeCases.values()]
      .filter((item) => item.status === "CLOSED")
      .map((item) => item.caseId)
      .sort();
    if (!/^[0-9]{4}-W[0-9]{2}$/.test(period))
      throw new Error("invalid rollover period");
    return {
      runId,
      period,
      dryRun: true,
      closedCaseIds,
      actions: [
        "FLUSH_CHANGED_CASES",
        "REFRESH_PROJECTIONS",
        "ROLLOVER_CLOSED_CASES",
        "UPDATE_ARCHIVE_INDEX",
      ],
      estimatedWrites: closedCaseIds.length * 3,
    };
  }

  applyFixtureRollover(
    plan: WeeklyMaintenancePlan,
    archivedAt: string,
  ): { rolledOver: number; duplicate: boolean } {
    if (this.completedRuns.has(plan.runId))
      return { rolledOver: 0, duplicate: true };
    let rolledOver = 0;
    for (const caseId of plan.closedCaseIds) {
      const active = this.activeCases.get(caseId);
      if (!active || active.status !== "CLOSED") continue;
      const archiveId = `archive_${plan.period.replace("-", "_")}_${caseId}`;
      this.archiveIndex.set(archiveId, {
        archiveId,
        caseId,
        period: plan.period,
        manifestId: `manifest_${caseId}_${active.changeVersion}`,
        archivedAt,
      });
      this.activeCases.delete(caseId);
      this.projections.delete(caseId);
      this.cache.delete(caseId);
      rolledOver += 1;
    }
    this.completedRuns.add(plan.runId);
    return { rolledOver, duplicate: false };
  }
}

export function simulateTriggerSchedule(
  startAtMs: number,
  intervalMinutes: number,
  count: number,
): number[] {
  if (!Number.isInteger(intervalMinutes) || intervalMinutes < 1) {
    throw new Error("intervalMinutes must be positive");
  }
  if (!Number.isInteger(count) || count < 0 || count > 100) {
    throw new Error("count must be between 0 and 100");
  }
  return Array.from(
    { length: count },
    (_, index) => startAtMs + index * intervalMinutes * 60_000,
  );
}
