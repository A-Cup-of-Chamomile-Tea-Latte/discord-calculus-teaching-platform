const previewLabels = {
  TRACKED: "預覽：教學團隊已接手（Tracked）",
  IDLE: "預覽：TA 最後留言後 48 小時無學生回覆，進入 Idle 並提醒",
  CLOSED: "預覽：負責人手動結案，標題加上 ✅",
  AUTO_CLOSED: "預覽：Idle 後再 48 小時無回覆，自動結案",
  REOPEN_CYCLE: "預覽：新追問建立下一個 Case Cycle 並回到 Tracked",
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
