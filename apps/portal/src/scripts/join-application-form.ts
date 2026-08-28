import {
  LOCAL_TEST_WINDOW_KEY,
  parseLocalTestWindow,
  remainingTestWindowMinutes,
} from "../lib/local-test-window";

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
  } else if (values.identityType === "TEACHING_TEAM") {
    const staffEmail = (values.staffEmail ?? "").toLowerCase();
    if (
      !emailPattern.test(staffEmail) ||
      !/@(?:[a-z0-9-]+\.)*ntu\.edu\.tw$/.test(staffEmail)
    ) {
      errors.staffEmail = "請使用臺大信箱（@ntu.edu.tw 或其子網域）。";
    }
    if (!new Set(["TA", "INSTRUCTOR"]).has(values.staffRole ?? "")) {
      errors.staffRole = "請選擇助教或教師。";
    }
    if (!/^(0[1-9]|1[0-6])$/.test(values.staffClassCode ?? "")) {
      errors.staffClassCode = "請選擇主要負責的 C01–C16 班別。";
    }
  } else {
    errors.identityType = "請選擇臺大學生、訪客或教學團隊。";
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

function csrfTokenFromCookie(name: string): string | null {
  const pair = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));
  return pair ? decodeURIComponent(pair.slice(name.length + 1)) : null;
}

function requestVerificationCode(
  dialog: HTMLDialogElement,
  destination: string,
): Promise<string | null> {
  const form = requiredElement<HTMLFormElement>(
    dialog,
    "[data-email-verification-form]",
  );
  const input = requiredElement<HTMLInputElement>(
    form,
    '[name="verificationCode"]',
  );
  const copy = requiredElement<HTMLElement>(
    form,
    "[data-email-verification-copy]",
  );
  const error = requiredElement<HTMLElement>(
    form,
    "[data-email-verification-error]",
  );
  const cancelButton = requiredElement<HTMLButtonElement>(
    form,
    "[data-email-verification-cancel]",
  );
  form.reset();
  copy.textContent = `驗證碼已排入寄送至 ${destination}，收到後請輸入六位數字。`;
  error.hidden = true;
  error.textContent = "";

  return new Promise((resolve) => {
    const finish = (value: string | null): void => {
      form.removeEventListener("submit", submit);
      cancelButton.removeEventListener("click", cancel);
      dialog.removeEventListener("cancel", cancelDialog);
      dialog.close();
      resolve(value);
    };
    const submit = (event: SubmitEvent): void => {
      event.preventDefault();
      const code = input.value.trim();
      if (!/^[0-9]{6}$/.test(code)) {
        error.textContent = "請輸入信件中的六位數驗證碼。";
        error.hidden = false;
        input.focus();
        return;
      }
      finish(code);
    };
    const cancel = (): void => finish(null);
    const cancelDialog = (event: Event): void => {
      event.preventDefault();
      finish(null);
    };
    form.addEventListener("submit", submit);
    cancelButton.addEventListener("click", cancel);
    dialog.addEventListener("cancel", cancelDialog);
    dialog.showModal();
    input.focus();
  });
}

function initialize(root: HTMLElement): void {
  const form = requiredElement<HTMLFormElement>(root, "form.prototype-form");
  const syntheticStaging = root.dataset.syntheticStaging === "true";
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

  // This build-time flag lets Rollup remove the reviewer-only local gate and
  // its storage key from the public bundle instead of shipping a dormant UI.
  const reviewMode = import.meta.env.PUBLIC_PORTAL_BUILD !== "true";
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
    const verificationDialog = requiredElement<HTMLDialogElement>(
      root,
      "[data-email-verification-dialog]",
    );
    const submitButton = requiredElement<HTMLButtonElement>(
      form,
      'button[type="submit"]',
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const values = runValidation();
      if (!values) return;
      const request = {
        ...values,
        rulesPrivacy: values.rulesPrivacy === "yes" ? "yes" : "no",
      };
      submitButton.disabled = true;
      submitButton.textContent = "準備寄送驗證碼…";
      if (state) {
        state.hidden = false;
        state.textContent = "正在建立 Email 驗證，請稍候。";
      }
      try {
        const sessionResponse = await fetch(sessionEndpoint, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({ scope: "JOIN" }).toString(),
        });
        const csrfToken = csrfTokenFromCookie("portal_join_csrf");
        if (!sessionResponse.ok || !csrfToken) throw new Error("session");
        const identityEmail =
          values.identityType === "STUDENT"
            ? values.ntuEmail
            : values.guestEmail;
        const emailStartResponse = await fetch(`${form.action}/email/start`, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": csrfToken,
          },
          body: new URLSearchParams({
            identityType: values.identityType,
            email: identityEmail,
          }).toString(),
        });
        if (!emailStartResponse.ok) {
          const failure = (await emailStartResponse
            .json()
            .catch(() => ({}))) as { error?: string };
          if (failure.error === "EMAIL_DESTINATION_REFUSED") {
            throw new Error("email-destination-refused");
          }
          throw new Error("email-start");
        }
        const started = (await emailStartResponse.json()) as {
          challengeId?: string;
        };
        if (!started.challengeId) throw new Error("email-challenge");
        submitButton.textContent = "等待 Email 驗證";
        const verificationCode = await requestVerificationCode(
          verificationDialog,
          identityEmail,
        );
        if (!verificationCode) throw new Error("email-cancelled");
        if (state) state.textContent = "正在確認驗證碼。";
        const emailVerifyResponse = await fetch(`${form.action}/email/verify`, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": csrfToken,
          },
          body: new URLSearchParams({
            challengeId: started.challengeId,
            code: verificationCode,
          }).toString(),
        });
        if (!emailVerifyResponse.ok) throw new Error("email-verify");
        const response = await fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": csrfToken,
          },
          body: new URLSearchParams({
            ...request,
            emailVerificationId: started.challengeId,
          }).toString(),
        });
        if (!response.ok) throw new Error("submit");
        form.hidden = true;
        if (state) {
          state.hidden = false;
          state.textContent = syntheticStaging
            ? "Synthetic Email 驗證與申請寫入皆已完成；沒有寄出真實 Email 或 Discord 私訊。"
            : "申請已收到，請留意 Discord 私訊。";
        }
      } catch (error) {
        if (state) {
          state.hidden = false;
          state.textContent =
            error instanceof Error &&
            error.message === "email-destination-refused"
              ? "這個隔離測試站不會寄信到真實地址；學生請使用 synthetic.student@ntu.edu.tw，訪客請使用 synthetic.guest@example.com。"
              : "Email 驗證或申請送出未完成。請確認驗證碼，稍後再試。";
        }
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "送出申請";
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
  const notice = requiredElement<HTMLElement>(
    root,
    "[data-test-registration-notice]",
  );
  const noticeTitle = requiredElement<HTMLElement>(
    notice,
    "[data-test-registration-title]",
  );
  const noticeDetail = requiredElement<HTMLElement>(
    notice,
    "[data-test-registration-detail]",
  );
  const testCodeForm = requiredElement<HTMLFormElement>(
    root,
    "[data-test-code-form]",
  );
  const testCodeInput = requiredElement<HTMLInputElement>(
    testCodeForm,
    '[name="testCode"]',
  );
  const testCodeMessage = requiredElement<HTMLElement>(
    testCodeForm,
    "[data-test-code-message]",
  );
  let showingConfirmation = false;
  let verifiedWindowOpenedAt: number | null = null;

  const activeTestWindow = () =>
    parseLocalTestWindow(localStorage.getItem(LOCAL_TEST_WINDOW_KEY));
  const renderTestWindow = (): void => {
    const windowState = activeTestWindow();
    if (!windowState) {
      localStorage.removeItem(LOCAL_TEST_WINDOW_KEY);
      notice.dataset.state = "closed";
      noticeTitle.textContent = "測試註冊尚未開放";
      noticeDetail.textContent =
        "請由系統管理員在「教學團隊登入」開放 Beta 註冊。";
      testCodeForm.hidden = true;
      verifiedWindowOpenedAt = null;
      if (!showingConfirmation) form.hidden = true;
      return;
    }
    const codeVerified = verifiedWindowOpenedAt === windowState.openedAt;
    notice.dataset.state = "open";
    if (windowState.mode === "CONTINUOUS") {
      noticeTitle.textContent = "Beta 註冊持續開放中";
      noticeDetail.textContent = codeVerified
        ? "測試碼已核對；將持續開放至管理員手動關閉。"
        : "請輸入現場管理員提供的六位測試碼。";
    } else {
      const closesAt = new Intl.DateTimeFormat("zh-TW", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(new Date(windowState.closesAt ?? 0));
      noticeTitle.textContent = "Beta 註冊臨時開放中";
      noticeDetail.textContent = codeVerified
        ? `測試碼已核對；將於 ${closesAt} 關閉，約剩 ${remainingTestWindowMinutes(windowState)} 分鐘。`
        : `請輸入現場管理員提供的六位測試碼；本次測試約剩 ${remainingTestWindowMinutes(windowState)} 分鐘。`;
    }
    testCodeForm.hidden = codeVerified || showingConfirmation;
    if (!showingConfirmation) form.hidden = !codeVerified;
  };

  renderTestWindow();
  window.setInterval(renderTestWindow, 15_000);

  testCodeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const windowState = activeTestWindow();
    const supplied = testCodeInput.value.trim();
    if (!windowState) {
      testCodeMessage.textContent = "本次測試已關閉，請向現場管理員確認。";
      renderTestWindow();
      return;
    }
    if (!/^[0-9]{6}$/.test(supplied) || supplied !== windowState.accessCode) {
      testCodeMessage.textContent = "測試碼不正確，請確認六位數字。";
      testCodeInput.select();
      return;
    }
    verifiedWindowOpenedAt = windowState.openedAt;
    testCodeForm.reset();
    testCodeMessage.textContent = "";
    renderTestWindow();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const windowState = activeTestWindow();
    if (!windowState || verifiedWindowOpenedAt !== windowState.openedAt) {
      renderTestWindow();
      return;
    }
    const values = runValidation();
    if (!values) return;

    const identityLabel =
      values.identityType === "GUEST"
        ? "訪客"
        : values.identityType === "TEACHING_TEAM"
          ? values.staffRole === "INSTRUCTOR"
            ? "教師"
            : "助教"
          : "臺大學生";
    requiredElement<HTMLElement>(
      confirmation,
      "[data-confirmation-identity]",
    ).textContent = identityLabel;
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
        : values.identityType === "TEACHING_TEAM"
          ? `${values.staffEmail}｜C${values.staffClassCode}`
          : `C${values.classCode}`;
    showingConfirmation = true;
    form.hidden = true;
    confirmation.hidden = false;
    confirmation.focus();
  });

  reset.addEventListener("click", () => {
    form.reset();
    clearErrors(form, errorSummary);
    showingConfirmation = false;
    confirmation.hidden = true;
    updateIdentity();
    renderTestWindow();
    if (!form.hidden) {
      form.querySelector<HTMLElement>("input, select, textarea")?.focus();
    }
  });
}

for (const root of document.querySelectorAll<HTMLElement>(
  "[data-join-application]",
)) {
  initialize(root);
}
