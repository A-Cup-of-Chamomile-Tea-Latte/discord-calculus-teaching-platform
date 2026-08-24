import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  createAliasPreview,
  createFixtureConfirmation,
  validateFixtureSubmission,
} from "./fixture-form-prototypes";

describe("fixture form prototypes", () => {
  it("creates a deterministic nnmmm alias preview", () => {
    expect(createAliasPreview("01")).toBe("01042");
    expect(createAliasPreview("02", 3)).toBe("02003");
    expect(createAliasPreview("x")).toBe("尚未選擇班別");
  });

  it("accepts a complete join fixture and rejects wrong email domains", () => {
    const valid = {
      identityType: "STUDENT",
      discordUsername: "dingding124816",
      ntuEmail: "student@ntu.edu.tw",
      contactGmail: "student.fixture@gmail.com",
      classCode: "01",
      rulesPrivacy: "yes",
    };
    expect(validateFixtureSubmission("join", valid)).toEqual({});
    expect(
      validateFixtureSubmission("join", { ...valid, classCode: "16" }),
    ).toEqual({});
    expect(
      validateFixtureSubmission("join", { ...valid, classCode: "21" }),
    ).toHaveProperty("classCode");
    expect(
      validateFixtureSubmission("join", {
        ...valid,
        ntuEmail: "student@example.com",
        contactGmail: "student@example.com",
      }),
    ).toMatchObject({
      ntuEmail: expect.any(String),
      contactGmail: expect.any(String),
    });
    expect(
      validateFixtureSubmission("join", {
        ...valid,
        discordUsername: "@dingding124816",
      }),
    ).toHaveProperty("discordUsername");
    expect(
      validateFixtureSubmission("join", {
        identityType: "GUEST",
        discordUsername: "guest.viewer",
        guestEmail: "visitor@example.org",
        guestReason: "我是校外教師，想觀摩課程討論方式。",
        rulesPrivacy: "yes",
      }),
    ).toEqual({});
  });

  it("accepts an anonymous general question after the NTU COOL acknowledgement", () => {
    const values = {
      title: "Fixture limit question",
      content:
        "This is fictional content long enough for local validation only.",
      visibility: "CLASS",
      authorDisplayMode: "ANONYMOUS",
      analysisPermission: "EXCLUDED",
      forum: "MATH",
      classCode: "01",
      module: "M1",
      mainTag: "觀念",
      problemType: "微積分觀念",
      coolAcknowledgement: "yes",
      attachmentName: "diagram-fixture.png (120 KB)",
    };
    expect(validateFixtureSubmission("question", values)).toEqual({});
    expect(
      validateFixtureSubmission("question", { ...values, module: "M4" }),
    ).toHaveProperty("module");
    expect(
      createFixtureConfirmation("question", values).summary,
    ).toContainEqual({ label: "作者顯示", value: "對一般成員匿名" });
    expect(
      createFixtureConfirmation("question", values).summary,
    ).toContainEqual({
      label: "Discord 標題預覽",
      value: "[M1 | C01][觀念] Fixture limit question",
    });
    expect(createFixtureConfirmation("question", values).reference).toMatch(
      /^C01-[A-HJ-NP-Z2-9]{6}-\d{4}-\d{4}$/,
    );
    expect(
      validateFixtureSubmission("question", {
        ...values,
        coolAcknowledgement: "",
      }),
    ).toHaveProperty("coolAcknowledgement");
  });

  it("keeps Private Support outside public lookup and analysis", () => {
    const values = {
      title: "Fixture private support request",
      content: "This is fictional private support content for validation only.",
      privacyAcknowledgement: "yes",
      analysisPermission: "EXCLUDED",
    };
    expect(validateFixtureSubmission("private-support", values)).toEqual({});
    expect(createFixtureConfirmation("private-support", values)).toMatchObject({
      publicLookup: false,
      persisted: false,
      reference: "C99-F6Q2S8-0723-1031-P",
    });
  });

  it("requires an explicit AI Yes/No decision and leaves the Portal radios unselected", () => {
    const values = {
      title: "Fixture AI decision",
      content: "This fictional content is long enough for local validation.",
      visibility: "CLASS",
      authorDisplayMode: "COURSE_ALIAS",
      analysisPermission: "",
      forum: "MATH",
      classCode: "01",
      module: "M1",
      mainTag: "觀念",
      problemType: "微積分觀念",
      coolAcknowledgement: "yes",
    };
    expect(validateFixtureSubmission("question", values)).toHaveProperty(
      "analysisPermission",
    );
    const source = readFileSync(
      new URL("../pages/ask/index.astro", import.meta.url),
      "utf8",
    );
    const analysisFieldset = source.slice(source.indexOf("是否允許 AI"));
    expect(
      analysisFieldset.slice(0, analysisFieldset.indexOf("</fieldset>")),
    ).not.toMatch(/checked/);
  });

  it("does not persist or transmit form data from the client script", () => {
    const script = readFileSync(
      new URL("../scripts/fixture-forms.ts", import.meta.url),
      "utf8",
    );
    expect(script).not.toMatch(
      /localStorage|sessionStorage|indexedDB|document\.cookie/,
    );
    expect(script).not.toMatch(/fetch\(|XMLHttpRequest|sendBeacon|WebSocket/);
  });
});
