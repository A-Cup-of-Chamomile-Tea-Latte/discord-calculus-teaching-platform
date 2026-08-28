export interface LocalTestWindow {
  version: 4;
  mode: "TEMPORARY" | "CONTINUOUS";
  accessCode: string;
  openedAt: number;
  closesAt: number | null;
}

export const LOCAL_TEST_WINDOW_KEY = "calculus-local-registration-gate-v4";
export const LOCAL_TEST_WINDOW_DURATION_MS = 30 * 60 * 1000;

export function createLocalTestCode(): string {
  const range = 1_000_000;
  const limit = Math.floor(0x1_0000_0000 / range) * range;
  const values = new Uint32Array(1);
  do {
    crypto.getRandomValues(values);
  } while (values[0]! >= limit);
  return String(values[0]! % range).padStart(6, "0");
}

export function createLocalTestWindow(
  accessCode: string,
  now = Date.now(),
  duration = LOCAL_TEST_WINDOW_DURATION_MS,
): LocalTestWindow {
  return {
    version: 4,
    mode: "TEMPORARY",
    accessCode,
    openedAt: now,
    closesAt: now + duration,
  };
}

export function createContinuousLocalTestWindow(
  accessCode: string,
  now = Date.now(),
): LocalTestWindow {
  return {
    version: 4,
    mode: "CONTINUOUS",
    accessCode,
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
      value.version !== 4 ||
      (value.mode !== "TEMPORARY" && value.mode !== "CONTINUOUS") ||
      typeof value.accessCode !== "string" ||
      !/^[0-9]{6}$/.test(value.accessCode) ||
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
