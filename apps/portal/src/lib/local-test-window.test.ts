import { describe, expect, it } from "vitest";

import {
  createContinuousLocalTestWindow,
  createLocalTestCode,
  createLocalTestWindow,
  parseLocalTestWindow,
  remainingTestWindowMinutes,
} from "./local-test-window";

describe("local test registration window", () => {
  it("creates a thirty-minute window by default", () => {
    const window = createLocalTestWindow("123456", 1_000);
    expect(window).toEqual({
      version: 4,
      mode: "TEMPORARY",
      accessCode: "123456",
      openedAt: 1_000,
      closesAt: 1_801_000,
    });
  });

  it("creates a continuous window that only an admin closes", () => {
    const window = createContinuousLocalTestWindow("654321", 1_000);
    expect(window).toEqual({
      version: 4,
      mode: "CONTINUOUS",
      accessCode: "654321",
      openedAt: 1_000,
      closesAt: null,
    });
    expect(parseLocalTestWindow(JSON.stringify(window), 99_999_999)).toEqual(
      window,
    );
  });

  it("accepts an active window and rejects expired or malformed state", () => {
    const active = createLocalTestWindow("123456", 1_000, 60_000);
    expect(parseLocalTestWindow(JSON.stringify(active), 30_000)).toEqual(
      active,
    );
    expect(parseLocalTestWindow(JSON.stringify(active), 61_000)).toBeNull();
    expect(parseLocalTestWindow("not-json", 1_000)).toBeNull();
  });

  it("rejects mismatched mode and expiry state", () => {
    expect(
      parseLocalTestWindow(
        JSON.stringify({
          version: 4,
          mode: "CONTINUOUS",
          accessCode: "123456",
          openedAt: 1_000,
          closesAt: 2_000,
        }),
        1_500,
      ),
    ).toBeNull();
  });

  it("rounds the remaining time up for the operator display", () => {
    const window = createLocalTestWindow("123456", 0, 90_001);
    expect(remainingTestWindowMinutes(window, 1)).toBe(2);
  });

  it("creates a six-digit code with leading zeroes allowed", () => {
    expect(createLocalTestCode()).toMatch(/^[0-9]{6}$/);
  });
});
