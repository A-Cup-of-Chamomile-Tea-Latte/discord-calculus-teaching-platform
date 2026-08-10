import { describe, expect, it } from "vitest";

import {
  carrierAnswers,
  evaluateSql,
  incorrectAnswerKeys,
  queueSnapshot,
  scoreAnswers,
  transactionSnapshot,
} from "./sqlite-lab";

describe("SQLite learning lab", () => {
  it("answers the four allowlisted read-only examples", () => {
    expect(evaluateSql(".tables").kind).toBe("text");
    expect(evaluateSql(".schema cases;").title).toBe("cases 的結構");
    expect(evaluateSql("SELECT COUNT(*) FROM cases;").rows).toEqual([["4"]]);
    expect(
      evaluateSql("SELECT status, COUNT(*) FROM cases GROUP BY status;").rows,
    ).toEqual([
      ["CLOSED", "1"],
      ["OPEN", "2"],
      ["TRACKED", "1"],
    ]);
  });

  it("intercepts broad and mutating queries", () => {
    expect(evaluateSql("SELECT * FROM cases;").kind).toBe("warning");
    expect(evaluateSql("DROP TABLE cases;").kind).toBe("warning");
    expect(evaluateSql("SELECT secret FROM unknown;").kind).toBe("error");
  });

  it("shows rollback versus partial state", () => {
    expect(transactionSnapshot("transaction", 3)).toMatchObject({
      caseState: "OPEN",
      databaseState: "一致",
    });
    expect(transactionSnapshot("unprotected", 3)).toMatchObject({
      caseState: "CLOSED",
      queueState: "遺失",
      databaseState: "不一致",
    });
  });

  it("rejects stale queue ownership in the learning sequence", () => {
    expect(queueSnapshot(1).workerA).toBe("持有目前 token");
    expect(queueSnapshot(4).workerA).toBe("完成請求遭拒");
    expect(queueSnapshot(99).job).toBe("VERIFIED");
  });

  it("scores carrier choices", () => {
    expect(scoreAnswers(carrierAnswers, carrierAnswers)).toEqual({
      correct: 5,
      total: 5,
    });
    expect(scoreAnswers({}, carrierAnswers)).toEqual({ correct: 0, total: 5 });
  });

  it("identifies the questions that need targeted review", () => {
    expect(
      incorrectAnswerKeys(
        { q1: "right", q2: "wrong" },
        { q1: "right", q2: "right", q3: "right" },
      ),
    ).toEqual(["q2", "q3"]);
  });
});
