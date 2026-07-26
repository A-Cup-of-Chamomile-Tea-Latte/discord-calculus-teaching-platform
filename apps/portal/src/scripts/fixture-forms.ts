import {
  createAliasPreview,
  createFixtureConfirmation,
  type FixtureFormKind,
  type FixtureFormValues,
  validateFixtureSubmission,
} from "../lib/fixture-form-prototypes";

function requiredElement<T extends Element>(
  root: ParentNode,
  selector: string,
): T {
  const element = root.querySelector<T>(selector);
  if (!element) throw new Error(`Fixture form is missing ${selector}`);
  return element;
}

function valuesFromForm(form: HTMLFormElement): FixtureFormValues {
  const values: FixtureFormValues = {};
  for (const [name, value] of new FormData(form).entries()) {
    if (typeof value === "string") values[name] = value;
  }
  return values;
}

function clearErrors(form: HTMLFormElement): void {
  for (const field of form.querySelectorAll<HTMLElement>("[aria-invalid]")) {
    field.removeAttribute("aria-invalid");
  }
  for (const message of form.querySelectorAll<HTMLElement>(
    "[data-field-error]",
  )) {
    message.hidden = true;
    message.textContent = "";
  }
}

function showErrors(
  form: HTMLFormElement,
  errors: Record<string, string>,
): void {
  const summary = requiredElement<HTMLElement>(form, "[data-form-errors]");
  const list = requiredElement<HTMLUListElement>(summary, "ul");
  list.replaceChildren();

  let firstInvalid: HTMLElement | undefined;
  for (const [name, message] of Object.entries(errors)) {
    const controls = Array.from(
      form.querySelectorAll<HTMLElement>(`[name="${name}"]`),
    );
    firstInvalid ??= controls[0];
    for (const control of controls)
      control.setAttribute("aria-invalid", "true");
    const fieldMessage = form.querySelector<HTMLElement>(
      `[data-field-error="${name}"]`,
    );
    if (fieldMessage) {
      fieldMessage.textContent = message;
      fieldMessage.hidden = false;
    }
    const item = document.createElement("li");
    item.textContent = message;
    list.append(item);
  }

  summary.hidden = false;
  summary.focus();
  firstInvalid?.scrollIntoView({ block: "center" });
}

function renderConfirmation(
  root: HTMLElement,
  kind: FixtureFormKind,
  values: FixtureFormValues,
): void {
  const form = requiredElement<HTMLFormElement>(root, "form");
  const confirmation = requiredElement<HTMLElement>(
    root,
    "[data-fixture-confirmation]",
  );
  const result = createFixtureConfirmation(kind, values);
  requiredElement<HTMLElement>(
    confirmation,
    "[data-confirmation-title]",
  ).textContent = result.title;
  requiredElement<HTMLElement>(
    confirmation,
    "[data-confirmation-reference]",
  ).textContent = result.reference;
  const summary = requiredElement<HTMLElement>(
    confirmation,
    "[data-confirmation-summary]",
  );
  summary.replaceChildren();
  for (const item of result.summary) {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = item.label;
    description.textContent = item.value;
    wrapper.append(term, description);
    summary.append(wrapper);
  }
  form.hidden = true;
  confirmation.hidden = false;
  confirmation.focus();
}

function initializeFixtureForm(root: HTMLElement): void {
  const kind = root.dataset.formKind as FixtureFormKind;
  const form = requiredElement<HTMLFormElement>(root, "form");
  const errorSummary = requiredElement<HTMLElement>(form, "[data-form-errors]");
  const confirmation = requiredElement<HTMLElement>(
    root,
    "[data-fixture-confirmation]",
  );
  const reset = requiredElement<HTMLButtonElement>(
    confirmation,
    "[data-fixture-reset]",
  );

  const classSelect = form.querySelector<HTMLSelectElement>(
    'select[name="classCode"]',
  );
  const aliasPreview = form.querySelector<HTMLOutputElement>(
    "[data-alias-preview]",
  );
  const updateAlias = (): void => {
    if (classSelect && aliasPreview) {
      aliasPreview.value = createAliasPreview(classSelect.value);
    }
  };
  classSelect?.addEventListener("change", updateAlias);
  updateAlias();

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearErrors(form);
    errorSummary.hidden = true;
    const values = valuesFromForm(form);
    const errors = validateFixtureSubmission(kind, values);
    if (Object.keys(errors).length > 0) {
      showErrors(form, errors);
      return;
    }
    renderConfirmation(root, kind, values);
  });

  reset.addEventListener("click", () => {
    form.reset();
    clearErrors(form);
    errorSummary.hidden = true;
    confirmation.hidden = true;
    form.hidden = false;
    updateAlias();
    form.querySelector<HTMLElement>("input, select, textarea")?.focus();
  });
}

for (const root of document.querySelectorAll<HTMLElement>(
  "[data-fixture-form]",
)) {
  initializeFixtureForm(root);
}
