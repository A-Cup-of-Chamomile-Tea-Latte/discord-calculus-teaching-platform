export interface LocalTestWindow {
  version: 3;
  mode: "TEMPORARY" | "CONTINUOUS";
  audience: "NTU_NETWORK" | "ANY";
  openedAt: number;
  closesAt: number | null;
}

export const LOCAL_TEST_WINDOW_KEY = "calculus-local-registration-gate-v3";
export const LOCAL_TEST_WINDOW_DURATION_MS = 30 * 60 * 1000;

export function createLocalTestWindow(
  now = Date.now(),
  duration = LOCAL_TEST_WINDOW_DURATION_MS,
  audience: LocalTestWindow["audience"] = "NTU_NETWORK",
): LocalTestWindow {
  return {
    version: 3,
    mode: "TEMPORARY",
    audience,
    openedAt: now,
    closesAt: now + duration,
  };
}

export function createContinuousLocalTestWindow(
  now = Date.now(),
  audience: LocalTestWindow["audience"] = "NTU_NETWORK",
): LocalTestWindow {
  return {
    version: 3,
    mode: "CONTINUOUS",
    audience,
    openedAt: now,
    closesAt: null,
  };
}

export function parseLocalTestWindow(
  raw: string | null,
  now = Date.now(),
): LocalTestWindow | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<LocalTestWindow>;
    if (
      value.version !== 3 ||
      (value.mode !== "TEMPORARY" && value.mode !== "CONTINUOUS") ||
      (value.audience !== "NTU_NETWORK" && value.audience !== "ANY") ||
      typeof value.openedAt !== "number" ||
      (value.mode === "TEMPORARY" &&
        (typeof value.closesAt !== "number" ||
          value.openedAt > value.closesAt ||
          value.closesAt <= now)) ||
      (value.mode === "CONTINUOUS" && value.closesAt !== null)
    ) {
      return null;
    }
    return value as LocalTestWindow;
  } catch {
    return null;
  }
}

export function remainingTestWindowMinutes(
  window: LocalTestWindow,
  now = Date.now(),
): number {
  if (window.closesAt === null) return 0;
  return Math.max(0, Math.ceil((window.closesAt - now) / 60_000));
}
