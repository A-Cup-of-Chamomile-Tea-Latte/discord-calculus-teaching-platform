const THEME_KEY = "calculus-portal-theme";
const allowedThemes = new Set(["formal", "student"]);

function readSavedTheme(): string {
  try {
    return localStorage.getItem(THEME_KEY) ?? "formal";
  } catch {
    return "formal";
  }
}

function saveTheme(theme: string): void {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // The selected theme still applies for this page when storage is blocked.
  }
}

function applyTheme(theme: string): void {
  const selected = allowedThemes.has(theme) ? theme : "formal";
  document.documentElement.dataset.theme = selected;
  document
    .querySelectorAll<HTMLButtonElement>("[data-theme-option]")
    .forEach((button) => {
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.themeOption === selected),
      );
    });
}

document
  .querySelectorAll<HTMLButtonElement>("[data-theme-option]")
  .forEach((button) => {
    button.addEventListener("click", () => {
      const selected = button.dataset.themeOption ?? "formal";
      saveTheme(selected);
      applyTheme(selected);
    });
  });

applyTheme(readSavedTheme());
