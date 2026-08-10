import { LOCAL_ACCESS_SESSION_KEY, validSession } from "../lib/local-access";

document
  .querySelectorAll<HTMLElement>("[data-local-signout]")
  .forEach((item) => {
    item.addEventListener("click", () => {
      try {
        sessionStorage.removeItem(LOCAL_ACCESS_SESSION_KEY);
      } catch {
        // The page still returns to guest mode after a reload when storage is blocked.
      }
      window.location.reload();
    });
  });

try {
  const raw = sessionStorage.getItem(LOCAL_ACCESS_SESSION_KEY);
  const session = raw ? JSON.parse(raw) : null;
  if (!validSession(session)) {
    sessionStorage.removeItem(LOCAL_ACCESS_SESSION_KEY);
    document.documentElement.dataset.accessRole = "guest";
  }
} catch {
  document.documentElement.dataset.accessRole = "guest";
}
