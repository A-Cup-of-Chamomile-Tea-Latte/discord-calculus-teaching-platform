import type { CaseStatus } from "./case-adapter";

export type ClosureSource = "MANUAL" | "AUTO";

export interface ClosurePolicy {
  temporaryCloseAfterDays: number;
  automaticCloseAfterDays: number;
}

export interface ClosureState {
  status: CaseStatus;
  lastUpdateAt: string;
  lastReadAt: string | null;
  closureSource: ClosureSource | null;
  closedAt: string | null;
  reopenedAt: string | null;
}

export const DEFAULT_CLOSURE_POLICY: Readonly<ClosurePolicy> = {
  temporaryCloseAfterDays: 3,
  automaticCloseAfterDays: 7,
};

const DAY_MS = 86_400_000;

function assertPolicy(policy: ClosurePolicy): void {
  if (
    !Number.isFinite(policy.temporaryCloseAfterDays) ||
    !Number.isFinite(policy.automaticCloseAfterDays) ||
    policy.temporaryCloseAfterDays <= 0 ||
    policy.automaticCloseAfterDays <= policy.temporaryCloseAfterDays
  ) {
    throw new Error("INVALID_CLOSURE_POLICY");
  }
}

function elapsedDays(from: string, to: string): number {
  const elapsed = new Date(to).getTime() - new Date(from).getTime();
  if (!Number.isFinite(elapsed)) throw new Error("INVALID_CLOSURE_TIMESTAMP");
  return elapsed / DAY_MS;
}

export function manualClose(state: ClosureState, at: string): ClosureState {
  return {
    ...state,
    status: "CLOSED",
    lastUpdateAt: at,
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
  const inactiveDays = elapsedDays(state.lastUpdateAt, now);

  if (
    state.status === "ANSWERED" &&
    state.lastReadAt !== null &&
    inactiveDays >= policy.temporaryCloseAfterDays
  ) {
    return {
      ...state,
      status: "TEMPORARILY_CLOSED",
      closureSource: "AUTO",
      closedAt: now,
    };
  }

  if (
    state.status === "TEMPORARILY_CLOSED" &&
    inactiveDays >= policy.automaticCloseAfterDays
  ) {
    return {
      ...state,
      status: "CLOSED",
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
  if (!["TEMPORARILY_CLOSED", "CLOSED"].includes(state.status)) {
    return { ...state, lastUpdateAt: at };
  }
  return {
    ...state,
    status: "REOPENED",
    lastUpdateAt: at,
    closureSource: null,
    closedAt: null,
    reopenedAt: at,
  };
}
