import {
  carrierAnswers,
  evaluateSql,
  incorrectAnswerKeys,
  queueSnapshot,
  scoreAnswers,
  transactionSnapshot,
  type TransactionMode,
} from "../lib/sqlite-lab";

const root = document.querySelector<HTMLElement>("[data-sqlite-lab]");

if (root) {
  const byId = <T extends HTMLElement>(id: string): T | null =>
    root.querySelector<T>(`#${id}`);

  const carrierDetails: Record<string, { title: string; body: string }> = {
    sqlite: {
      title: "本機 SQLite｜真實運作狀態",
      body: "案件、工作佇列與交易一致性以本機 SQLite 為準。兩隻 Bot 可以用同一套明確的結構協作，無須另外架設資料庫伺服器。",
    },
    sheet: {
      title: "Google Sheets｜給人看的受控投影",
      body: "只放 TA 需要閱讀或低頻操作的充分統計量，例如案件待辦、成員驗證摘要與 Bot 健康狀態。它不是完整備份。",
    },
    archive: {
      title: "受管檔案｜大而敏感的內容",
      body: "原始訊息、隱密案件、附件與匯出內容留在有清單、檢查碼與保留規則的檔案區。",
    },
    git: {
      title: "Git 文字檔｜規則與可審查歷史",
      body: "資料結構、升級規則、程式與政策適合用文字檔儲存，因為可以比較差異、審查與測試；它不儲存即時記錄。",
    },
  };

  root
    .querySelectorAll<HTMLButtonElement>("[data-carrier]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.carrier ?? "sqlite";
        const detail = carrierDetails[key];
        if (!detail) return;
        root
          .querySelectorAll<HTMLButtonElement>("[data-carrier]")
          .forEach((candidate) =>
            candidate.setAttribute(
              "aria-pressed",
              String(candidate === button),
            ),
          );
        const title = byId<HTMLElement>("carrier-detail-title");
        const body = byId<HTMLElement>("carrier-detail-body");
        if (title) title.textContent = detail.title;
        if (body) body.textContent = detail.body;
      });
    });

  const schemaDetails: Record<string, string> = {
    case_id:
      "內部主鍵（primary key）。每一列都必須唯一，程式用它穩定地找到同一案件。",
    case_number: "給人使用的案號，另有 UNIQUE 限制，避免兩個案件拿到相同案號。",
    status:
      "目前狀態，例如 OPEN、TRACKED、CLOSED。這是運作狀態，不是完整歷史。",
    module_code:
      "案件所屬課程模組。常用於篩選，但是否需要索引，必須看實際查詢。",
    created_at: "建立時間。用明確時區格式儲存，避免不同環境各自猜測。",
  };
  root
    .querySelectorAll<HTMLButtonElement>("[data-column]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.column ?? "case_id";
        root
          .querySelectorAll<HTMLButtonElement>("[data-column]")
          .forEach((candidate) =>
            candidate.setAttribute(
              "aria-pressed",
              String(candidate === button),
            ),
          );
        const output = byId<HTMLElement>("column-explanation");
        if (output) output.textContent = schemaDetails[key] ?? "";
      });
    });

  const queryInput = byId<HTMLTextAreaElement>("sql-input");
  root
    .querySelectorAll<HTMLButtonElement>("[data-sql-preset]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        if (!queryInput) return;
        queryInput.value = button.dataset.sqlPreset ?? "";
        queryInput.focus();
      });
    });

  const renderSqlResult = () => {
    if (!queryInput) return;
    const result = evaluateSql(queryInput.value);
    const output = byId<HTMLElement>("sql-output");
    const title = byId<HTMLElement>("sql-output-title");
    const message = byId<HTMLElement>("sql-output-message");
    const tableWrap = byId<HTMLElement>("sql-output-table");
    if (!output || !title || !message || !tableWrap) return;
    output.dataset.kind = result.kind;
    title.textContent = result.title;
    message.textContent = result.message;
    tableWrap.replaceChildren();
    if (result.kind === "table" && result.columns && result.rows) {
      const table = document.createElement("table");
      const head = document.createElement("thead");
      const headRow = document.createElement("tr");
      for (const column of result.columns) {
        const cell = document.createElement("th");
        cell.scope = "col";
        cell.textContent = column;
        headRow.append(cell);
      }
      head.append(headRow);
      const body = document.createElement("tbody");
      for (const row of result.rows) {
        const rowElement = document.createElement("tr");
        for (const value of row) {
          const cell = document.createElement("td");
          cell.textContent = value;
          rowElement.append(cell);
        }
        body.append(rowElement);
      }
      table.append(head, body);
      tableWrap.append(table);
    } else if (result.kind === "text") {
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = result.message;
      pre.append(code);
      tableWrap.append(pre);
      message.textContent = "";
    }
  };
  byId<HTMLButtonElement>("run-sql")?.addEventListener(
    "click",
    renderSqlResult,
  );

  let transactionMode: TransactionMode = "transaction";
  let transactionStep = 0;
  const renderTransaction = () => {
    const snapshot = transactionSnapshot(transactionMode, transactionStep);
    const step = byId<HTMLElement>("transaction-step");
    const caseState = byId<HTMLElement>("transaction-case");
    const queueState = byId<HTMLElement>("transaction-queue");
    const state = byId<HTMLElement>("transaction-consistency");
    const explanation = byId<HTMLElement>("transaction-explanation");
    if (step) step.textContent = `${transactionStep + 1} / 4`;
    if (caseState) caseState.textContent = snapshot.caseState;
    if (queueState) queueState.textContent = snapshot.queueState;
    if (state) {
      state.textContent = snapshot.databaseState;
      state.dataset.state = snapshot.databaseState;
    }
    if (explanation) explanation.textContent = snapshot.explanation;
    const next = byId<HTMLButtonElement>("transaction-next");
    if (next) next.disabled = transactionStep >= 3;
  };
  root
    .querySelectorAll<HTMLButtonElement>("[data-transaction-mode]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        transactionMode =
          button.dataset.transactionMode === "unprotected"
            ? "unprotected"
            : "transaction";
        transactionStep = 0;
        root
          .querySelectorAll<HTMLButtonElement>("[data-transaction-mode]")
          .forEach((candidate) =>
            candidate.setAttribute(
              "aria-pressed",
              String(candidate === button),
            ),
          );
        renderTransaction();
      });
    });
  byId<HTMLButtonElement>("transaction-next")?.addEventListener("click", () => {
    transactionStep = Math.min(3, transactionStep + 1);
    renderTransaction();
  });
  byId<HTMLButtonElement>("transaction-reset")?.addEventListener(
    "click",
    () => {
      transactionStep = 0;
      renderTransaction();
    },
  );
  renderTransaction();

  let queueStepIndex = 0;
  const renderQueue = () => {
    const snapshot = queueSnapshot(queueStepIndex);
    const step = byId<HTMLElement>("queue-step");
    const job = byId<HTMLElement>("queue-job");
    const workerA = byId<HTMLElement>("queue-worker-a");
    const workerB = byId<HTMLElement>("queue-worker-b");
    const explanation = byId<HTMLElement>("queue-explanation");
    if (step) step.textContent = `${queueStepIndex + 1} / 6`;
    if (job) job.textContent = snapshot.job;
    if (workerA) workerA.textContent = snapshot.workerA;
    if (workerB) workerB.textContent = snapshot.workerB;
    if (explanation) explanation.textContent = snapshot.explanation;
    const next = byId<HTMLButtonElement>("queue-next");
    if (next) next.disabled = queueStepIndex >= 5;
  };
  byId<HTMLButtonElement>("queue-next")?.addEventListener("click", () => {
    queueStepIndex = Math.min(5, queueStepIndex + 1);
    renderQueue();
  });
  byId<HTMLButtonElement>("queue-reset")?.addEventListener("click", () => {
    queueStepIndex = 0;
    renderQueue();
  });
  renderQueue();

  const diagnosticAnswers: Record<string, string> = {
    d1: "no",
    d2: "rollback",
    d3: "lease",
  };
  const diagnosticModules: Record<string, string> = {
    d1: "07 雲端驗證",
    d2: "04 交易",
    d3: "05 可靠工作佇列",
  };
  byId<HTMLButtonElement>("check-diagnostic")?.addEventListener("click", () => {
    const form = byId<HTMLFormElement>("diagnostic-quiz");
    const output = byId<HTMLElement>("diagnostic-result");
    if (!form || !output) return;
    const answers = Object.fromEntries(new FormData(form).entries()) as Record<
      string,
      string
    >;
    const unanswered = Object.keys(diagnosticAnswers).filter(
      (key) => !answers[key],
    );
    if (unanswered.length > 0) {
      output.textContent = `還有 ${unanswered.length} 題未作答。猜也可以，這裡不計分。`;
      return;
    }
    const missed = incorrectAnswerKeys(answers, diagnosticAnswers).map(
      (key) => diagnosticModules[key],
    );
    output.textContent =
      missed.length === 0
        ? "三題直覺都對。後面會用模擬把理由補齊。"
        : `直覺已記下。特別留意：${missed.join("、")}。`;
  });

  byId<HTMLButtonElement>("check-carriers")?.addEventListener("click", () => {
    const form = byId<HTMLFormElement>("carrier-quiz");
    const output = byId<HTMLElement>("carrier-score");
    if (!form || !output) return;
    const answers = Object.fromEntries(new FormData(form).entries()) as Record<
      string,
      string
    >;
    const score = scoreAnswers(answers, carrierAnswers);
    const carrierTopics: Record<string, string> = {
      caseAuthority: "案件真實狀態",
      memberSummary: "成員驗證摘要",
      rawAttachment: "原始附件",
      migrationRule: "結構與升級規則",
      discordToken: "Discord token",
    };
    const missed = incorrectAnswerKeys(answers, carrierAnswers).map(
      (key) => carrierTopics[key],
    );
    output.textContent =
      score.correct === score.total
        ? "5 / 5。你已能依資料性質選擇載體。"
        : `${score.correct} / ${score.total}。請再判斷：${missed.join("、")}。`;
    output.dataset.complete = String(score.correct === score.total);
  });

  byId<HTMLButtonElement>("verify-receipt")?.addEventListener("click", () => {
    const gates = [
      ...root.querySelectorAll<HTMLInputElement>("[data-authenticity-gate]"),
    ];
    const output = byId<HTMLElement>("receipt-result");
    if (!output) return;
    const missing = gates
      .filter((gate) => !gate.checked)
      .map((gate) => gate.dataset.label ?? "未完成檢查");
    if (missing.length === 0) {
      output.textContent =
        "可以進入人工確認後的受控匯入流程；這仍不等於自動覆蓋 SQLite。";
      output.dataset.state = "accepted";
    } else {
      output.textContent = `拒絕匯入。尚缺：${missing.join("、")}。`;
      output.dataset.state = "rejected";
    }
  });

  const finalAnswers: Record<string, string> = {
    q1: "local",
    q2: "rollback",
    q3: "lease",
    q4: "projection",
    q5: "confirm",
    q6: "later",
  };
  const finalModules: Record<string, string> = {
    q1: "01 資料地圖",
    q2: "04 交易",
    q3: "05 可靠工作佇列",
    q4: "01 資料地圖",
    q5: "07 雲端驗證",
    q6: "02 結構與限制",
  };
  byId<HTMLButtonElement>("check-final-quiz")?.addEventListener("click", () => {
    const form = byId<HTMLFormElement>("final-quiz");
    const output = byId<HTMLElement>("final-score");
    if (!form || !output) return;
    const answers = Object.fromEntries(new FormData(form).entries()) as Record<
      string,
      string
    >;
    const score = scoreAnswers(answers, finalAnswers);
    const missed = [
      ...new Set(
        incorrectAnswerKeys(answers, finalAnswers).map(
          (key) => finalModules[key],
        ),
      ),
    ];
    output.textContent =
      score.correct >= 5
        ? `${score.correct} / 6。你已掌握本頁的主要判斷框架，可以進入可拋棄資料庫的實作課。${missed.length > 0 ? `實作前再看：${missed.join("、")}。` : ""}`
        : `${score.correct} / 6。建議重看：${missed.join("、")}。`;
    output.dataset.complete = String(score.correct >= 5);
  });

  const progressKey = "calculus-sqlite-lab-progress-v1";
  const modules = [
    ...root.querySelectorAll<HTMLElement>("[data-learning-module]"),
  ].map((section) => section.dataset.learningModule ?? "");
  let completed = new Set<string>();
  try {
    const stored = JSON.parse(localStorage.getItem(progressKey) ?? "[]");
    if (Array.isArray(stored)) completed = new Set(stored.map(String));
  } catch {
    completed = new Set();
  }
  const renderProgress = () => {
    const count = modules.filter((module) => completed.has(module)).length;
    const percent = Math.round((count / modules.length) * 100);
    const text = byId<HTMLElement>("learning-progress-text");
    const bar = byId<HTMLElement>("learning-progress-bar");
    if (text)
      text.textContent = `${count} / ${modules.length} 節 · ${percent}%`;
    if (bar) bar.style.width = `${percent}%`;
    root
      .querySelectorAll<HTMLButtonElement>("[data-complete-module]")
      .forEach((button) => {
        const module = button.dataset.completeModule ?? "";
        const isComplete = completed.has(module);
        button.setAttribute("aria-pressed", String(isComplete));
        button.textContent = isComplete ? "已完成這一節" : "標記這一節完成";
      });
    root.querySelectorAll<HTMLElement>("[data-module-link]").forEach((link) => {
      link.dataset.complete = String(
        completed.has(link.dataset.moduleLink ?? ""),
      );
    });
  };
  const saveProgress = () => {
    try {
      localStorage.setItem(progressKey, JSON.stringify([...completed]));
    } catch {
      // Progress is optional; the lab remains usable when storage is unavailable.
    }
    renderProgress();
  };
  root
    .querySelectorAll<HTMLButtonElement>("[data-complete-module]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        const module = button.dataset.completeModule ?? "";
        if (completed.has(module)) completed.delete(module);
        else completed.add(module);
        saveProgress();
      });
    });
  byId<HTMLButtonElement>("reset-learning-progress")?.addEventListener(
    "click",
    () => {
      completed.clear();
      saveProgress();
    },
  );
  renderProgress();
}
