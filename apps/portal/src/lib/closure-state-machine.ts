import type { CaseStatus } from "./case-adapter";

export type ClosureSource = "MANUAL" | "AUTO";

export interface ClosurePolicy {
  idleAfterHours: number;
  autoCloseAfterIdleHours: number;
}

export interface ClosureState {
  status: CaseStatus;
  lastActivityAt: string;
  lastTeachingResponseAt: string | null;
  idleAt: string | null;
  closureSource: ClosureSource | null;
  closedAt: string | null;
  reopenedAt: string | null;
}

export const DEFAULT_CLOSURE_POLICY: Readonly<ClosurePolicy> = {
  idleAfterHours: 48,
  autoCloseAfterIdleHours: 48,
};

const HOUR_MS = 3_600_000;

function assertPolicy(policy: ClosurePolicy): void {
  if (
    !Number.isFinite(policy.idleAfterHours) ||
    !Number.isFinite(policy.autoCloseAfterIdleHours) ||
    policy.idleAfterHours <= 0 ||
    policy.autoCloseAfterIdleHours <= 0
  ) {
    throw new Error("INVALID_CLOSURE_POLICY");
  }
}

function elapsedHours(from: string, to: string): number {
  const elapsed = new Date(to).getTime() - new Date(from).getTime();
  if (!Number.isFinite(elapsed)) throw new Error("INVALID_CLOSURE_TIMESTAMP");
  return elapsed / HOUR_MS;
}

export function manualClose(
  state: ClosureState,
  at: string,
  actor: { isResponsibleStaff: boolean },
): ClosureState {
  if (!actor.isResponsibleStaff) throw new Error("MANUAL_CLOSE_NOT_ALLOWED");
  return {
    ...state,
    status: "CLOSED",
    lastActivityAt: at,
    idleAt: null,
    closureSource: "MANUAL",
    closedAt: at,
  };
}

export function applyAutomaticClosure(
  state: ClosureState,
  now: string,
  policy: ClosurePolicy = DEFAULT_CLOSURE_POLICY,
): ClosureState {
  assertPolicy(policy);

  if (
    state.status === "TRACKED" &&
    state.lastTeachingResponseAt !== null &&
    elapsedHours(state.lastTeachingResponseAt, now) >= policy.idleAfterHours
  ) {
    return {
      ...state,
      status: "IDLE",
      idleAt: now,
      closureSource: null,
      closedAt: null,
    };
  }

  if (
    state.status === "IDLE" &&
    state.idleAt !== null &&
    elapsedHours(state.idleAt, now) >= policy.autoCloseAfterIdleHours
  ) {
    return {
      ...state,
      status: "AUTO_CLOSED",
      closureSource: "AUTO",
      closedAt: now,
    };
  }

  return state;
}

export function recordNewActivity(
  state: ClosureState,
  at: string,
): ClosureState {
  const wasClosed = state.status === "CLOSED" || state.status === "AUTO_CLOSED";
  if (state.status === "OPEN" || state.status === "TRACKED") {
    return { ...state, lastActivityAt: at };
  }
  return {
    ...state,
    status: "TRACKED",
    lastActivityAt: at,
    idleAt: null,
    closureSource: null,
    closedAt: null,
    reopenedAt: wasClosed ? at : state.reopenedAt,
  };
}
