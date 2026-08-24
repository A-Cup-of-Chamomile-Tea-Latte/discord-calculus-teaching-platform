import type { CaseStatusView } from "../lib/case-adapter";
import { lookupCaseStatus } from "../lib/client-case-lookup";

type CaseSegmentName = "course" | "token" | "date" | "time" | "private";

const segmentNames: CaseSegmentName[] = [
  "course",
  "token",
  "date",
  "time",
  "private",
];

function splitCaseNumber(
  value: string,
): Record<CaseSegmentName, string> | null {
  const normalized = value.trim().toUpperCase().replace(/\s+/g, "");
  const match =
    /^([A-Z0-9]{3})-([A-Z0-9]{6})-([0-9]{4})-([0-9]{4})(?:-(P))?$/.exec(
      normalized,
    );
  if (!match) return null;
  return {
    course: match[1],
    token: match[2],
    date: match[3],
    time: match[4],
    private: match[5] ?? "",
  };
}

const statusLabels = {
  OPEN: "○ 新案件",
  TRACKED: "✓ 進行中",
  IDLE: "↩ 等待回覆",
  CLOSED: "■ 已結案",
  AUTO_CLOSED: "◇ 已自動結案",
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
  if (root.dataset.caseSearchEnabled !== "true") return;
  const form = requiredElement<HTMLFormElement>(root, "form");
  const input = requiredElement<HTMLInputElement>(root, "[data-case-value]");
  const control = requiredElement<HTMLElement>(
    root,
    "[data-case-number-control]",
  );
  const segmentInputs = segmentNames.map((name) =>
    requiredElement<HTMLInputElement>(root, `[data-case-segment="${name}"]`),
  );
  const states = Array.from(
    root.querySelectorAll<HTMLElement>("[data-search-state]"),
  );
  const dataElement = requiredElement<HTMLScriptElement>(
    root,
    "[data-case-fixtures]",
  );
  const cases = JSON.parse(dataElement.textContent ?? "[]") as CaseStatusView[];
  const syncUrl = root.dataset.syncUrl === "true";

  const sanitizeSegment = (
    inputElement: HTMLInputElement,
    name: CaseSegmentName,
  ): void => {
    const digitsOnly = name === "date" || name === "time";
    inputElement.value = inputElement.value
      .toUpperCase()
      .replace(digitsOnly ? /[^0-9]/g : /[^A-Z0-9]/g, "")
      .slice(0, inputElement.maxLength);
    if (name === "private" && inputElement.value !== "P") {
      inputElement.value = "";
    }
  };

  const composeCaseNumber = (): string => {
    const [course, token, date, time, privateSuffix] = segmentInputs.map(
      (segment) => segment.value,
    );
    return [course, token, date, time, privateSuffix]
      .filter((value, index) => index < 4 || value.length > 0)
      .join("-");
  };

  const syncHiddenValue = (): void => {
    input.value = composeCaseNumber();
  };

  const populateSegments = (value: string): boolean => {
    const parsed = splitCaseNumber(value);
    if (!parsed) return false;
    for (const [index, name] of segmentNames.entries()) {
      segmentInputs[index].value = parsed[name];
    }
    syncHiddenValue();
    return true;
  };

  const setInvalid = (invalid: boolean): void => {
    if (invalid) control.dataset.invalid = "true";
    else delete control.dataset.invalid;
    for (const segment of segmentInputs) {
      if (invalid) segment.setAttribute("aria-invalid", "true");
      else segment.removeAttribute("aria-invalid");
    }
  };

  const showState = (name: string): void => {
    for (const state of states)
      state.hidden = state.dataset.searchState !== name;
  };

  const runLookup = (rawValue: string): void => {
    showState("loading");
    queueMicrotask(() => {
      const result = lookupCaseStatus(cases, rawValue);
      input.value = result.normalizedCaseNumber;
      populateSegments(result.normalizedCaseNumber);
      if (syncUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set("case", result.normalizedCaseNumber);
        window.history.replaceState({}, "", url);
      }
      if (result.outcome === "INVALID") {
        setInvalid(true);
        showState("invalid");
        return;
      }
      setInvalid(false);
      if (result.outcome === "NOT_FOUND") {
        showState("not-found");
        return;
      }

      requiredElement<HTMLElement>(root, "[data-result-number]").textContent =
        result.case.caseNumber;
      requiredElement<HTMLElement>(root, "[data-result-type]").textContent =
        result.case.caseType === "PRIVATE_SUPPORT" ? "隱密案件" : "一般案件";
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
      requiredElement<HTMLElement>(root, "[data-result-replied]").textContent =
        result.case.teachingTeamReplied ? "已有回覆" : "尚無回覆";
      const discordLink = requiredElement<HTMLAnchorElement>(
        root,
        "[data-result-link]",
      );
      const noLink = requiredElement<HTMLElement>(
        root,
        "[data-result-no-link]",
      );
      if (result.case.discordDeepLink) {
        discordLink.href = result.case.discordDeepLink;
        discordLink.hidden = false;
        noLink.hidden = true;
      } else {
        discordLink.removeAttribute("href");
        discordLink.hidden = true;
        noLink.hidden = false;
      }
      showState("found");
    });
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    syncHiddenValue();
    runLookup(input.value);
  });

  for (const [index, segment] of segmentInputs.entries()) {
    const name = segmentNames[index];
    segment.addEventListener("input", () => {
      sanitizeSegment(segment, name);
      syncHiddenValue();
      setInvalid(false);
      if (
        segment.value.length === segment.maxLength &&
        index < segmentInputs.length - 1
      ) {
        segmentInputs[index + 1].focus();
      }
    });

    segment.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && segment.value === "" && index > 0) {
        segmentInputs[index - 1].focus();
      }
    });

    segment.addEventListener("paste", (event) => {
      const pastedValue = event.clipboardData?.getData("text") ?? "";
      if (!populateSegments(pastedValue)) return;
      event.preventDefault();
      const lastFilledIndex = segmentInputs[4].value ? 4 : 3;
      segmentInputs[lastFilledIndex].focus();
    });
  }

  if (syncUrl) {
    const initialValue = new URL(window.location.href).searchParams.get("case");
    if (initialValue) {
      input.value = initialValue;
      populateSegments(initialValue);
      runLookup(initialValue);
    }
  }
}

for (const root of document.querySelectorAll<HTMLElement>(
  "[data-case-search]",
)) {
  initializeCaseSearch(root);
}
