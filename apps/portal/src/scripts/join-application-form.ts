type JoinValues = Record<string, string>;

function requiredElement<T extends Element>(
  root: ParentNode,
  selector: string,
): T {
  const element = root.querySelector<T>(selector);
  if (!element) throw new Error(`Join application is missing ${selector}`);
  return element;
}

function valuesFromForm(form: HTMLFormElement): JoinValues {
  const values: JoinValues = {};
  for (const [name, value] of new FormData(form).entries()) {
    if (typeof value === "string") values[name] = value.trim();
  }
  return values;
}

function validate(values: JoinValues): Record<string, string> {
  const errors: Record<string, string> = {};
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const username = values.discordUsername ?? "";
  if (username.length < 2 || username.length > 32 || /[@#:\s]/.test(username)) {
    errors.discordUsername =
      "請填寫 2–32 個字元的 Discord 使用者名稱，不要加 @、# 或空格。";
  }
  if (values.identityType === "STUDENT") {
    const ntuEmail = (values.ntuEmail ?? "").toLowerCase();
    const gmail = (values.contactGmail ?? "").toLowerCase();
    if (!emailPattern.test(ntuEmail) || !ntuEmail.endsWith("@ntu.edu.tw")) {
      errors.ntuEmail = "請使用格式完整的 NTU Mail（結尾為 @ntu.edu.tw）。";
    }
    if (gmail && (!emailPattern.test(gmail) || !gmail.endsWith("@gmail.com"))) {
      errors.contactGmail = "請使用結尾為 @gmail.com 的地址，或將欄位留空。";
    }
    if (!/^(0[1-9]|1[0-6])$/.test(values.classCode ?? "")) {
      errors.classCode = "請選擇 C01–C16 的正式班別。";
    }
  } else if (values.identityType === "GUEST") {
    if (!emailPattern.test((values.guestEmail ?? "").toLowerCase())) {
      errors.guestEmail = "請填寫可聯絡的 Email。";
    }
    const reasonLength = (values.guestReason ?? "").length;
    if (reasonLength < 10 || reasonLength > 500) {
      errors.guestReason = "請用 10–500 個字元簡短說明來訪原因。";
    }
  } else {
    errors.identityType = "請選擇臺大學生或訪客。";
  }
  if (values.rulesPrivacy !== "yes") {
    errors.rulesPrivacy = "請先確認已閱讀使用與隱私說明。";
  }
  return errors;
}

function clearErrors(form: HTMLFormElement, errorSummary: HTMLElement): void {
  errorSummary.hidden = true;
  for (const control of form.querySelectorAll<HTMLElement>("[aria-invalid]")) {
    control.removeAttribute("aria-invalid");
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
  errorSummary: HTMLElement,
  errors: Record<string, string>,
): void {
  const list = requiredElement<HTMLUListElement>(errorSummary, "ul");
  list.replaceChildren();
  for (const [name, message] of Object.entries(errors)) {
    for (const control of form.querySelectorAll<HTMLElement>(
      `[name="${name}"]`,
    )) {
      control.setAttribute("aria-invalid", "true");
    }
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
  errorSummary.hidden = false;
  errorSummary.focus();
}

function csrfTokenFromCookie(): string | null {
  const pair = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("portal_csrf="));
  return pair ? decodeURIComponent(pair.slice("portal_csrf=".length)) : null;
}

function initialize(root: HTMLElement): void {
  const form = requiredElement<HTMLFormElement>(root, "form");
  const errorSummary = requiredElement<HTMLElement>(form, "[data-form-errors]");
  const updateIdentity = (): void => {
    const identity = form.querySelector<HTMLInputElement>(
      'input[name="identityType"]:checked',
    )?.value;
    for (const group of form.querySelectorAll<HTMLElement>(
      "[data-identity-fields]",
    )) {
      const active = group.dataset.identityFields === identity;
      group.hidden = !active;
      for (const control of group.querySelectorAll<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >("input, select, textarea")) {
        control.disabled = !active;
      }
    }
  };
  form
    .querySelectorAll<HTMLInputElement>('input[name="identityType"]')
    .forEach((control) => control.addEventListener("change", updateIdentity));
  updateIdentity();

  const reviewMode = root.dataset.reviewMode === "true";
  const sessionEndpoint = root.dataset.sessionEndpoint;
  const runValidation = (): JoinValues | null => {
    clearErrors(form, errorSummary);
    const values = valuesFromForm(form);
    const errors = validate(values);
    if (Object.keys(errors).length > 0) {
      showErrors(form, errorSummary, errors);
      return null;
    }
    return values;
  };

  if (!reviewMode && sessionEndpoint && form.action) {
    const state = root.querySelector<HTMLElement>("[data-join-backend-state]");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const values = runValidation();
      if (!values) return;
      const request = {
        ...values,
        rulesPrivacy: values.rulesPrivacy === "yes" ? "yes" : "no",
      };
      try {
        const sessionResponse = await fetch(sessionEndpoint, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        const csrfToken = csrfTokenFromCookie();
        if (!sessionResponse.ok || !csrfToken) throw new Error("session");
        const response = await fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": csrfToken,
          },
          body: new URLSearchParams(request).toString(),
        });
        if (!response.ok) throw new Error("submit");
        form.hidden = true;
        if (state) {
          state.hidden = false;
          state.textContent = "申請已收到，請留意 Discord 私訊。";
        }
      } catch {
        if (state) {
          state.hidden = false;
          state.textContent = "目前無法送出申請，請稍後再試。";
        }
      }
    });
    return;
  }

  if (!reviewMode) return;
  const confirmation = requiredElement<HTMLElement>(
    root,
    "[data-join-confirmation]",
  );
  const reset = requiredElement<HTMLButtonElement>(
    confirmation,
    "[data-join-reset]",
  );

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const values = runValidation();
    if (!values) return;

    requiredElement<HTMLElement>(
      confirmation,
      "[data-confirmation-identity]",
    ).textContent = values.identityType === "GUEST" ? "訪客" : "臺大學生";
    requiredElement<HTMLElement>(
      confirmation,
      "[data-confirmation-username]",
    ).textContent = values.discordUsername;
    requiredElement<HTMLElement>(
      confirmation,
      "[data-confirmation-detail]",
    ).textContent =
      values.identityType === "GUEST"
        ? values.guestEmail
        : `C${values.classCode}`;
    form.hidden = true;
    confirmation.hidden = false;
    confirmation.focus();
  });

  reset.addEventListener("click", () => {
    form.reset();
    clearErrors(form, errorSummary);
    confirmation.hidden = true;
    form.hidden = false;
    updateIdentity();
    form.querySelector<HTMLElement>("input, select, textarea")?.focus();
  });
}

for (const root of document.querySelectorAll<HTMLElement>(
  "[data-join-application]",
)) {
  initialize(root);
}
