import {
  LOCAL_ACCESS_SESSION_KEY,
  LOCAL_ACCESS_STORE_KEY,
  SESSION_DURATION_MS,
  createEmptyAccessStore,
  createLocalAccount,
  hashAccountId,
  normalizeAccountId,
  passwordPolicyError,
  replaceLocalPassword,
  type LocalAccessSession,
  type LocalAccessStore,
  type LocalAccount,
  type LocalRole,
  validSession,
  verifyLocalAccount,
} from "../lib/local-access";
import {
  LOCAL_TEST_WINDOW_KEY,
  createContinuousLocalTestWindow,
  createLocalTestWindow,
  parseLocalTestWindow,
  remainingTestWindowMinutes,
} from "../lib/local-test-window";

const root = document.querySelector<HTMLElement>("[data-local-access]");
const LOCAL_ACCESS_ARCHIVE_KEY = "calculus-local-access-archive-v1";

if (root) {
  const required = <T extends Element>(selector: string): T => {
    const element = root.querySelector<T>(selector);
    if (!element) throw new Error(`Local access is missing ${selector}`);
    return element;
  };

  const views = [...root.querySelectorAll<HTMLElement>("[data-access-view]")];
  const showView = (name: string): void => {
    for (const view of views) view.hidden = view.dataset.accessView !== name;
  };

  const setMessage = (
    selector: string,
    message: string,
    state: "error" | "success" | "working" = "error",
  ): void => {
    const element = required<HTMLElement>(selector);
    element.textContent = message;
    element.dataset.state = state;
  };

  const readStore = (): LocalAccessStore => {
    try {
      const raw = localStorage.getItem(LOCAL_ACCESS_STORE_KEY);
      if (!raw) return createEmptyAccessStore();
      const value = JSON.parse(raw) as Partial<LocalAccessStore>;
      if (
        value.version !== 1 ||
        typeof value.accountLookupSalt !== "string" ||
        !Array.isArray(value.accounts)
      ) {
        throw new Error("INVALID_LOCAL_ACCESS_STORE");
      }
      return value as LocalAccessStore;
    } catch {
      return createEmptyAccessStore();
    }
  };

  const saveStore = (store: LocalAccessStore): void => {
    localStorage.setItem(LOCAL_ACCESS_STORE_KEY, JSON.stringify(store));
  };

  const readSession = (): LocalAccessSession | null => {
    try {
      const raw = sessionStorage.getItem(LOCAL_ACCESS_SESSION_KEY);
      const value = raw ? JSON.parse(raw) : null;
      return validSession(value) ? value : null;
    } catch {
      return null;
    }
  };

  const testerWindow = root.querySelector<HTMLElement>("[data-tester-window]");
  const renderTesterWindow = (): void => {
    if (!testerWindow) return;
    const session = readSession();
    testerWindow.hidden = session?.role !== "admin";
    if (testerWindow.hidden) return;

    const state = parseLocalTestWindow(
      localStorage.getItem(LOCAL_TEST_WINDOW_KEY),
    );
    const stateLabel = required<HTMLElement>("[data-test-window-state]");
    const detail = required<HTMLElement>("[data-test-window-detail]");
    const openButton = required<HTMLButtonElement>("[data-open-test-window]");
    const continuousButton = required<HTMLButtonElement>(
      "[data-open-continuous-window]",
    );
    const closeButton = required<HTMLButtonElement>("[data-close-test-window]");
    const audienceControl = required<HTMLInputElement>(
      "[data-test-window-audience]",
    );
    if (!state) {
      localStorage.removeItem(LOCAL_TEST_WINDOW_KEY);
      stateLabel.textContent = "尚未開放";
      detail.textContent = "可開放 30 分鐘測試，或持續開放至管理員手動關閉。";
      openButton.disabled = false;
      continuousButton.disabled = false;
      closeButton.disabled = true;
      audienceControl.disabled = false;
      return;
    }
    const audienceText =
      state.audience === "NTU_NETWORK"
        ? "限臺大校內網路／SSL VPN"
        : "不限連線來源";
    audienceControl.checked = state.audience === "NTU_NETWORK";
    audienceControl.disabled = true;
    if (state.mode === "CONTINUOUS") {
      stateLabel.textContent = "持續開放中";
      detail.textContent = `${audienceText}；將持續開放，直到管理員手動關閉。`;
    } else {
      const closesAt = new Intl.DateTimeFormat("zh-TW", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(new Date(state.closesAt ?? 0));
      stateLabel.textContent = "臨時開放中";
      detail.textContent = `${audienceText}；將於 ${closesAt} 關閉，約剩 ${remainingTestWindowMinutes(state)} 分鐘。`;
    }
    openButton.disabled = true;
    continuousButton.disabled = true;
    closeButton.disabled = false;
  };

  const startSession = (account: LocalAccount): void => {
    const session: LocalAccessSession = {
      accountHash: account.accountHash,
      role: account.role,
      expiresAt: Date.now() + SESSION_DURATION_MS,
    };
    sessionStorage.setItem(LOCAL_ACCESS_SESSION_KEY, JSON.stringify(session));
    window.location.assign(new URL("../access/", window.location.href).href);
  };

  const requestedRole = new URL(window.location.href).searchParams.get("role");
  const expectedRole: LocalRole = requestedRole === "staff" ? "staff" : "admin";
  required<HTMLInputElement>('[name="expectedRole"]').value = expectedRole;
  root
    .querySelectorAll<HTMLElement>("[data-login-role-label]")
    .forEach((item) => {
      item.textContent = expectedRole === "staff" ? "助教／教師" : "系統管理員";
    });
  required<HTMLElement>("[data-login-message]").textContent =
    expectedRole === "admin"
      ? "請使用第一位管理員或由其新增的系統管理員帳號登入。"
      : "請使用系統管理員建立的助教／教師帳號登入。";
  root
    .querySelectorAll<HTMLAnchorElement>("[data-role-tab]")
    .forEach((item) => {
      item.setAttribute(
        "aria-current",
        item.dataset.roleTab === expectedRole ? "page" : "false",
      );
    });

  let store = readStore();
  let pendingAccount: LocalAccount | null = null;
  let pendingAccountId = "";
  let failedAttempts = 0;

  const renderAccountView = (session: LocalAccessSession): void => {
    showView("account");
    root
      .querySelectorAll<HTMLElement>("[data-current-role]")
      .forEach((item) => {
        item.textContent =
          session.role === "admin" ? "系統管理員" : "助教／教師";
      });
    const adminOnly = required<HTMLElement>("[data-admin-only]");
    adminOnly.hidden = session.role !== "admin";
    renderTesterWindow();
  };

  const existingSession = readSession();
  if (existingSession) renderAccountView(existingSession);
  else if (store.accounts.length === 0) showView("bootstrap");
  else showView("login");

  required<HTMLFormElement>("[data-bootstrap-form]").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      if (store.accounts.length !== 0) {
        showView("login");
        return;
      }
      const formElement = event.currentTarget as HTMLFormElement;
      const form = new FormData(formElement);
      const accountId = String(form.get("accountId") ?? "");
      const password = String(form.get("password") ?? "");
      const confirmation = String(form.get("passwordConfirmation") ?? "");
      const policyError = passwordPolicyError(password, accountId);
      if (!normalizeAccountId(accountId)) {
        setMessage("[data-bootstrap-message]", "請輸入管理員帳號。");
        return;
      }
      if (policyError) {
        setMessage("[data-bootstrap-message]", policyError);
        return;
      }
      if (password !== confirmation) {
        setMessage("[data-bootstrap-message]", "兩次輸入的密碼不一致。");
        return;
      }
      setMessage("[data-bootstrap-message]", "正在建立本機管理員…", "working");
      const account = await createLocalAccount(
        accountId,
        "admin",
        store.accountLookupSalt,
        { password, mustChangePassword: false },
      );
      store.accounts.push(account);
      saveStore(store);
      formElement.reset();
      setMessage(
        "[data-login-message]",
        "本機系統管理員已建立，請登入。",
        "success",
      );
      showView("login");
    },
  );

  required<HTMLButtonElement>("[data-reinitialize-access]").addEventListener(
    "click",
    () => {
      const existing = localStorage.getItem(LOCAL_ACCESS_STORE_KEY);
      if (existing) localStorage.setItem(LOCAL_ACCESS_ARCHIVE_KEY, existing);
      sessionStorage.removeItem(LOCAL_ACCESS_SESSION_KEY);
      store = createEmptyAccessStore();
      saveStore(store);
      setMessage(
        "[data-bootstrap-message]",
        "舊測試身份已移到這個瀏覽器的暫存區。現在可建立新的本機管理員。",
        "success",
      );
      showView("bootstrap");
    },
  );

  root
    .querySelector<HTMLButtonElement>("[data-open-test-window]")
    ?.addEventListener("click", () => {
      if (readSession()?.role !== "admin") return;
      const audience = required<HTMLInputElement>("[data-test-window-audience]")
        .checked
        ? "NTU_NETWORK"
        : "ANY";
      localStorage.setItem(
        LOCAL_TEST_WINDOW_KEY,
        JSON.stringify(createLocalTestWindow(Date.now(), undefined, audience)),
      );
      renderTesterWindow();
    });

  root
    .querySelector<HTMLButtonElement>("[data-open-continuous-window]")
    ?.addEventListener("click", () => {
      if (readSession()?.role !== "admin") return;
      const audience = required<HTMLInputElement>("[data-test-window-audience]")
        .checked
        ? "NTU_NETWORK"
        : "ANY";
      localStorage.setItem(
        LOCAL_TEST_WINDOW_KEY,
        JSON.stringify(createContinuousLocalTestWindow(Date.now(), audience)),
      );
      renderTesterWindow();
    });

  root
    .querySelector<HTMLButtonElement>("[data-close-test-window]")
    ?.addEventListener("click", () => {
      if (readSession()?.role !== "admin") return;
      localStorage.removeItem(LOCAL_TEST_WINDOW_KEY);
      renderTesterWindow();
    });

  window.setInterval(renderTesterWindow, 15_000);

  required<HTMLFormElement>("[data-login-form]").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      if (failedAttempts >= 5) {
        setMessage(
          "[data-login-message]",
          "這個分頁已連續失敗五次。請重新整理後再試。",
        );
        return;
      }
      const formElement = event.currentTarget as HTMLFormElement;
      const form = new FormData(formElement);
      const accountId = String(form.get("accountId") ?? "");
      const password = String(form.get("password") ?? "");
      const expected = String(form.get("expectedRole") ?? "admin");
      setMessage("[data-login-message]", "正在核對…", "working");
      const accountHash = await hashAccountId(
        accountId,
        store.accountLookupSalt,
      );
      const account = store.accounts.find(
        (candidate) => candidate.accountHash === accountHash,
      );
      const verified = account
        ? await verifyLocalAccount(account, password)
        : false;
      if (!account || !verified || account.role !== expected) {
        failedAttempts += 1;
        setMessage(
          "[data-login-message]",
          `帳號、密碼或身份不符。還可嘗試 ${Math.max(0, 5 - failedAttempts)} 次。`,
        );
        return;
      }
      failedAttempts = 0;
      if (account.mustChangePassword) {
        pendingAccount = account;
        pendingAccountId = normalizeAccountId(accountId);
        showView("force-change");
        return;
      }
      startSession(account);
    },
  );

  required<HTMLFormElement>("[data-force-change-form]").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      if (!pendingAccount) return;
      const formElement = event.currentTarget as HTMLFormElement;
      const form = new FormData(formElement);
      const password = String(form.get("password") ?? "");
      const confirmation = String(form.get("passwordConfirmation") ?? "");
      const policyError = passwordPolicyError(password, pendingAccountId);
      if (policyError) {
        setMessage("[data-force-change-message]", policyError);
        return;
      }
      if (password !== confirmation) {
        setMessage("[data-force-change-message]", "兩次輸入的新密碼不一致。");
        return;
      }
      const updated = await replaceLocalPassword(pendingAccount, password);
      store.accounts = store.accounts.map((account) =>
        account.accountHash === updated.accountHash ? updated : account,
      );
      saveStore(store);
      startSession(updated);
    },
  );

  required<HTMLFormElement>("[data-add-account-form]").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      const session = readSession();
      if (!session || session.role !== "admin") return;
      const formElement = event.currentTarget as HTMLFormElement;
      const form = new FormData(formElement);
      const accountId = String(form.get("accountId") ?? "");
      const role = form.get("role") === "admin" ? "admin" : "staff";
      const accountHash = await hashAccountId(
        accountId,
        store.accountLookupSalt,
      );
      if (
        store.accounts.some((account) => account.accountHash === accountHash)
      ) {
        setMessage("[data-add-account-message]", "這個本機帳號已存在。");
        return;
      }
      setMessage(
        "[data-add-account-message]",
        "正在建立一次性登入…",
        "working",
      );
      const account = await createLocalAccount(
        accountId,
        role,
        store.accountLookupSalt,
      );
      store.accounts.push(account);
      saveStore(store);
      formElement.reset();
      setMessage(
        "[data-add-account-message]",
        "帳號已加入。初始密碼與帳號相同，首次登入會強制更改。",
        "success",
      );
    },
  );

  required<HTMLFormElement>("[data-change-password-form]").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      const session = readSession();
      if (!session) return;
      const formElement = event.currentTarget as HTMLFormElement;
      const form = new FormData(formElement);
      const accountId = String(form.get("accountId") ?? "");
      const currentPassword = String(form.get("currentPassword") ?? "");
      const password = String(form.get("password") ?? "");
      const confirmation = String(form.get("passwordConfirmation") ?? "");
      const accountHash = await hashAccountId(
        accountId,
        store.accountLookupSalt,
      );
      const account = store.accounts.find(
        (candidate) => candidate.accountHash === session.accountHash,
      );
      if (
        !account ||
        accountHash !== session.accountHash ||
        !(await verifyLocalAccount(account, currentPassword))
      ) {
        setMessage("[data-change-password-message]", "目前帳號或密碼不正確。");
        return;
      }
      const policyError = passwordPolicyError(password, accountId);
      if (policyError) {
        setMessage("[data-change-password-message]", policyError);
        return;
      }
      if (password !== confirmation) {
        setMessage(
          "[data-change-password-message]",
          "兩次輸入的新密碼不一致。",
        );
        return;
      }
      const updated = await replaceLocalPassword(account, password);
      store.accounts = store.accounts.map((candidate) =>
        candidate.accountHash === updated.accountHash ? updated : candidate,
      );
      saveStore(store);
      formElement.reset();
      setMessage(
        "[data-change-password-message]",
        "密碼已更新；本機仍只保存 salt 與雜湊。",
        "success",
      );
    },
  );
}
