import type { PublicCaseView } from "../lib/case-adapter";
import { lookupPublicCase } from "../lib/client-case-lookup";

const statusLabels = {
  OPEN: "○ Open · 待接手",
  WAITING_FOR_STUDENT: "↩ Idle · 等待學生",
  ANSWERED: "✓ Tracked · 已接手",
  ESCALATED: "↑ Tracked · 已升級",
  TEMPORARILY_CLOSED: "◐ Idle · 提醒中",
  CLOSED: "■ Closed · 已結案",
  REOPENED: "↻ Tracked · 新循環",
} as const;

function requiredElement<T extends Element>(
  root: ParentNode,
  selector: string,
): T {
  const element = root.querySelector<T>(selector);
  if (!element) throw new Error(`CaseSearch is missing ${selector}`);
  return element;
}

function initializeCaseSearch(root: HTMLElement): void {
  const form = requiredElement<HTMLFormElement>(root, "form");
  const input = requiredElement<HTMLInputElement>(root, 'input[name="case"]');
  const states = Array.from(
    root.querySelectorAll<HTMLElement>("[data-search-state]"),
  );
  const dataElement = requiredElement<HTMLScriptElement>(
    root,
    "[data-case-fixtures]",
  );
  const cases = JSON.parse(dataElement.textContent ?? "[]") as PublicCaseView[];
  const syncUrl = root.dataset.syncUrl === "true";
  const detailBase = root.dataset.detailBase ?? "/cases/";

  const showState = (name: string): void => {
    for (const state of states)
      state.hidden = state.dataset.searchState !== name;
  };

  const runLookup = (rawValue: string): void => {
    showState("loading");
    queueMicrotask(() => {
      const result = lookupPublicCase(cases, rawValue);
      input.value = result.normalizedCaseNumber;
      if (syncUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set("case", result.normalizedCaseNumber);
        window.history.replaceState({}, "", url);
      }
      if (result.outcome === "INVALID") {
        input.setAttribute("aria-invalid", "true");
        showState("invalid");
        return;
      }
      input.removeAttribute("aria-invalid");
      if (result.outcome === "NOT_FOUND") {
        showState("not-found");
        return;
      }

      requiredElement<HTMLElement>(root, "[data-result-number]").textContent =
        result.case.caseNumber;
      requiredElement<HTMLElement>(root, "[data-result-title]").textContent =
        result.case.title;
      requiredElement<HTMLElement>(root, "[data-result-status]").textContent =
        statusLabels[result.case.status];
      requiredElement<HTMLTimeElement>(root, "[data-result-updated]").dateTime =
        result.case.updatedAt;
      requiredElement<HTMLTimeElement>(
        root,
        "[data-result-updated]",
      ).textContent = new Intl.DateTimeFormat("zh-TW", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(result.case.updatedAt));
      const detailLink = requiredElement<HTMLAnchorElement>(
        root,
        "[data-result-link]",
      );
      detailLink.href = `${detailBase}${encodeURIComponent(result.case.caseNumber)}/`;
      showState("found");
    });
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runLookup(input.value);
  });

  if (syncUrl) {
    const initialValue = new URL(window.location.href).searchParams.get("case");
    if (initialValue) {
      input.value = initialValue;
      runLookup(initialValue);
    }
  }
}

for (const root of document.querySelectorAll<HTMLElement>(
  "[data-case-search]",
)) {
  initializeCaseSearch(root);
}
