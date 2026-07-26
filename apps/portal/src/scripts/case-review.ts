const previewLabels = {
  TEMPORARILY_CLOSED:
    "預覽：暫時結案（AUTO；必須具備 VERIFIED_VIEW 且符合設定門檻）",
  CLOSED: "預覽：手動結案（MANUAL）",
  REOPENED: "預覽：新活動使已關閉案件重新開啟",
} as const;

for (const root of document.querySelectorAll<HTMLElement>(
  "[data-lifecycle-review]",
)) {
  const result = root.querySelector<HTMLElement>("[data-transition-result]");
  if (!result) continue;
  for (const button of root.querySelectorAll<HTMLButtonElement>(
    "[data-preview-transition]",
  )) {
    button.addEventListener("click", () => {
      const transition = button.dataset
        .previewTransition as keyof typeof previewLabels;
      result.textContent = `${previewLabels[transition]}。Fixture only；未保存。`;
    });
  }
}
