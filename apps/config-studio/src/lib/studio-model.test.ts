import { describe, expect, it } from "vitest";

import {
  canonicalTitlePreview,
  classifyImport,
  computeChannelDiff,
  type StudioChannel,
} from "./studio-model";

const channel: StudioChannel = {
  key: "math",
  name: "Math Questions",
  type: "FORUM",
  parent: "questions",
  topic: "",
  slowmodeSeconds: 0,
  autoArchiveMinutes: 10080,
  enabled: true,
  managedCase: true,
  forumTags: ["觀念"],
  permissions: {},
};

describe("config studio model", () => {
  it("classifies added, modified, removed, and unchanged channels", () => {
    const modified = { ...channel, name: "Math Questions 2" };
    const added = { ...channel, key: "other", name: "Other" };
    expect(computeChannelDiff([channel], [modified, added])).toEqual([
      { kind: "MODIFY", key: "math", detail: "將修改 Math Questions 2" },
      { kind: "ADD", key: "other", detail: "將新增 Other" },
    ]);
    expect(computeChannelDiff([channel], [])).toEqual([
      { kind: "REMOVE", key: "math", detail: "將移除 Math Questions" },
    ]);
    expect(computeChannelDiff([channel], [channel])[0]?.kind).toBe("UNCHANGED");
  });

  it("builds the confirmed canonical title format", () => {
    expect(canonicalTitlePreview("M1", "01", "觀念", "我不懂 chain rule")).toBe(
      "[M1 | C01][觀念] 我不懂 chain rule",
    );
  });

  it("treats imported documents as classified preview input", () => {
    expect(classifyImport("", "hello").accepted).toBe(false);
    expect(classifyImport("人工備註", "").accepted).toBe(false);
    expect(classifyImport("人工備註", "hello").accepted).toBe(true);
  });
});
