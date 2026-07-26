import { describe, expect, it } from "vitest";

import { joinBase, normalizeBase } from "./paths";

describe("base-path helpers", () => {
  it("keeps root builds rooted", () => {
    expect(normalizeBase("/")).toBe("/");
    expect(joinBase("/", "cases/")).toBe("/cases/");
  });

  it("normalizes a GitHub Pages project base", () => {
    expect(normalizeBase("discord-calculus-teaching-platform")).toBe(
      "/discord-calculus-teaching-platform/",
    );
    expect(joinBase("/discord-calculus-teaching-platform/", "/guide/")).toBe(
      "/discord-calculus-teaching-platform/guide/",
    );
  });
});
