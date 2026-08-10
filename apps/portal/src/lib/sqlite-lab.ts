export interface LabResult {
  kind: "table" | "text" | "warning" | "error";
  title: string;
  columns?: string[];
  rows?: string[][];
  message: string;
}

const syntheticCases = [
  ["CASE-A01", "OPEN", "M1"],
  ["CASE-A02", "TRACKED", "M3"],
  ["CASE-A03", "CLOSED", "M2"],
  ["CASE-A04", "OPEN", "M1"],
];

function normalizeSql(input: string): string {
  return input.trim().replace(/\s+/g, " ").replace(/;$/, "").toLowerCase();
}

export function evaluateSql(input: string): LabResult {
  const normalized = normalizeSql(input);
  if (normalized === ".tables") {
    return {
      kind: "text",
      title: "資料表清單",
      message:
        "cases  drafts  private_dump_jobs  private_support  runtime_config  schema_migrations",
    };
  }
  if (normalized === ".schema cases") {
    return {
      kind: "text",
      title: "cases 的結構",
      message:
        "CREATE TABLE cases (case_id TEXT PRIMARY KEY, case_number TEXT NOT NULL UNIQUE, status TEXT NOT NULL, module_code TEXT NOT NULL, created_at TEXT NOT NULL);",
    };
  }
  if (normalized === "select count(*) from cases") {
    return {
      kind: "table",
      title: "總案件數",
      columns: ["COUNT(*)"],
      rows: [[String(syntheticCases.length)]],
      message: "只取得一個數字，沒有讀出案件內容。",
    };
  }
  if (normalized === "select status, count(*) from cases group by status") {
    return {
      kind: "table",
      title: "依狀態分組",
      columns: ["status", "COUNT(*)"],
      rows: [
        ["CLOSED", "1"],
        ["OPEN", "2"],
        ["TRACKED", "1"],
      ],
      message: "這是充分統計量：足以回答問題，不需要搬出完整資料列。",
    };
  }
  if (
    normalized === "select case_number, status, module_code from cases limit 3"
  ) {
    return {
      kind: "table",
      title: "限制欄位與筆數",
      columns: ["case_number", "status", "module_code"],
      rows: syntheticCases.slice(0, 3),
      message: "只選需要的欄位，並用 LIMIT 限制展示筆數。",
    };
  }
  if (/^select \* from cases(?: limit \d+)?$/.test(normalized)) {
    return {
      kind: "warning",
      title: "查詢被教學護欄攔下",
      message:
        "SELECT * 會把每個欄位都讀出來。先問清楚目的，再改成只選必要欄位；這也是避免意外曝露資料的好習慣。",
    };
  }
  if (
    /\b(insert|update|delete|drop|alter|create|replace|attach|pragma)\b/.test(
      normalized,
    )
  ) {
    return {
      kind: "warning",
      title: "這個實驗台只允許唯讀查詢",
      message:
        "修改結構或資料必須在 disposable database 另行練習；這裡不執行寫入指令。",
    };
  }
  return {
    kind: "error",
    title: "尚未辨識這個查詢",
    message:
      "先使用上方四個範例。這個實驗台是教學模擬器，不是完整 SQLite engine。",
  };
}

export type TransactionMode = "transaction" | "unprotected";

export interface TransactionSnapshot {
  caseState: string;
  queueState: string;
  databaseState: "一致" | "不一致";
  explanation: string;
}

export function transactionSnapshot(
  mode: TransactionMode,
  step: number,
): TransactionSnapshot {
  const boundedStep = Math.max(0, Math.min(step, 3));
  if (boundedStep === 0) {
    return {
      caseState: "OPEN",
      queueState: "尚無工作",
      databaseState: "一致",
      explanation: "起點：案件仍開啟，也還沒有匯出工作。",
    };
  }
  if (boundedStep === 1) {
    return {
      caseState: mode === "transaction" ? "準備改為 CLOSED" : "CLOSED",
      queueState: "準備建立",
      databaseState: "一致",
      explanation:
        mode === "transaction"
          ? "交易已開始，但變更尚未對其他讀者生效。"
          : "第一個寫入已立即生效，現在只能期待第二個寫入也成功。",
    };
  }
  if (boundedStep === 2) {
    return {
      caseState: mode === "transaction" ? "暫存 CLOSED" : "CLOSED",
      queueState: "寫入前發生錯誤",
      databaseState: mode === "transaction" ? "一致" : "不一致",
      explanation:
        mode === "transaction"
          ? "錯誤發生時，SQLite 準備 rollback 整組變更。"
          : "案件已關閉，但匯出工作不存在；兩個事實互相矛盾。",
    };
  }
  return mode === "transaction"
    ? {
        caseState: "OPEN",
        queueState: "尚無工作",
        databaseState: "一致",
        explanation: "ROLLBACK 完成：回到原本可重試的狀態，沒有留下半套結果。",
      }
    : {
        caseState: "CLOSED",
        queueState: "遺失",
        databaseState: "不一致",
        explanation: "沒有交易就無法自動復原；現在需要人工補償與稽核。",
      };
}

export interface QueueSnapshot {
  job: string;
  workerA: string;
  workerB: string;
  explanation: string;
}

const queueSnapshots: QueueSnapshot[] = [
  {
    job: "PENDING",
    workerA: "等待",
    workerB: "等待",
    explanation: "工作已建立，但還沒有人取得處理權。",
  },
  {
    job: "CLAIMED · lease A",
    workerA: "持有目前 token",
    workerB: "不得處理",
    explanation: "Worker A 原子取得 claim；其他 worker 必須退讓。",
  },
  {
    job: "CLAIMED · lease 已到期",
    workerA: "逾時",
    workerB: "可重新 claim",
    explanation: "A 沒有 heartbeat，lease 到期，工作不會永遠卡死。",
  },
  {
    job: "CLAIMED · lease B",
    workerA: "舊 token",
    workerB: "持有目前 token",
    explanation: "Worker B 接手，取得新的 token 與 lease。",
  },
  {
    job: "CLAIMED · lease B",
    workerA: "完成請求遭拒",
    workerB: "仍在處理",
    explanation: "A 即使晚回來，也不能用過期 token 覆寫 B 的工作。",
  },
  {
    job: "VERIFIED",
    workerA: "退出",
    workerB: "完成",
    explanation: "只有目前 token 的持有人能提交最終狀態。",
  },
];

export function queueSnapshot(step: number): QueueSnapshot {
  return queueSnapshots[
    Math.max(0, Math.min(step, queueSnapshots.length - 1))
  ]!;
}

export const carrierAnswers: Record<string, string> = {
  caseAuthority: "sqlite",
  memberSummary: "sheet",
  rawAttachment: "archive",
  migrationRule: "git",
  discordToken: "secret",
};

export function scoreAnswers(
  answers: Record<string, string>,
  expected: Record<string, string>,
): { correct: number; total: number } {
  const entries = Object.entries(expected);
  return {
    correct: entries.filter(([key, value]) => answers[key] === value).length,
    total: entries.length,
  };
}
