import {
  canonicalTitlePreview,
  classifyImport,
  cloneBundle,
  computeChannelDiff,
  type StudioBundle,
  type StudioChannel,
} from "../lib/studio-model";

function byId<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLElement))
    throw new Error(`MISSING_ELEMENT:${id}`);
  return element as T;
}

const dataNode = byId<HTMLScriptElement>("studio-data");
const parsed = JSON.parse(dataNode.textContent ?? "{}") as StudioBundle;
const source = cloneBundle(parsed);
const state = cloneBundle(parsed);

const dirtyStatus = byId<HTMLElement>("dirty-status");
const channelList = byId<HTMLElement>("channel-list");
const diffList = byId<HTMLElement>("diff-list");
const importText = byId<HTMLTextAreaElement>("import-text");
const importKind = byId<HTMLSelectElement>("import-kind");
const importStatus = byId<HTMLElement>("import-status");

function markDirty(): void {
  dirtyStatus.textContent = "有尚未匯出的本機變更";
  dirtyStatus.dataset.dirty = "true";
}

function escapeText(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return entities[character] ?? character;
  });
}

function channelTemplate(channel: StudioChannel, index: number): string {
  const tags = channel.forumTags.length ? channel.forumTags.join("、") : "—";
  return `
    <article class="editor-row" data-channel-key="${escapeText(channel.key)}">
      <div class="editor-row__grip" aria-hidden="true">${index + 1}</div>
      <div class="editor-row__main">
        <label>
          <span>名稱</span>
          <input data-channel-name="${index}" value="${escapeText(channel.name)}" />
        </label>
        <div class="editor-row__meta">
          <span class="type-chip">${channel.type}</span>
          <span>${escapeText(channel.parent)}</span>
          <span>${channel.enabled ? "第一版啟用" : "動態樣板"}</span>
          <span>${channel.managedCase ? "案件" : "非案件"}</span>
        </div>
        <p>${escapeText(channel.topic)}</p>
        <small>標籤：${escapeText(tags)}</small>
      </div>
      <div class="editor-row__actions">
        <button type="button" class="quiet" data-move-up="${index}" aria-label="向上移動 ${escapeText(channel.name)}">↑</button>
        <button type="button" class="quiet" data-move-down="${index}" aria-label="向下移動 ${escapeText(channel.name)}">↓</button>
      </div>
    </article>`;
}

function renderChannels(): void {
  channelList.innerHTML = state.server.channels.map(channelTemplate).join("");
  channelList
    .querySelectorAll<HTMLInputElement>("[data-channel-name]")
    .forEach((input) => {
      input.addEventListener("input", () => {
        const index = Number(input.dataset.channelName);
        const selected = state.server.channels[index];
        if (!selected) return;
        selected.name = input.value;
        markDirty();
        renderDiff();
      });
    });
  channelList
    .querySelectorAll<HTMLButtonElement>("[data-move-up]")
    .forEach((button) => {
      button.addEventListener("click", () =>
        moveChannel(Number(button.dataset.moveUp), -1),
      );
    });
  channelList
    .querySelectorAll<HTMLButtonElement>("[data-move-down]")
    .forEach((button) => {
      button.addEventListener("click", () =>
        moveChannel(Number(button.dataset.moveDown), 1),
      );
    });
  applyChannelSearch();
}

function moveChannel(index: number, delta: number): void {
  const destination = index + delta;
  if (destination < 0 || destination >= state.server.channels.length) return;
  const [selected] = state.server.channels.splice(index, 1);
  if (!selected) return;
  state.server.channels.splice(destination, 0, selected);
  markDirty();
  renderChannels();
  renderDiff();
}

function renderDiff(): void {
  const diffs = computeChannelDiff(
    source.server.channels,
    state.server.channels,
  );
  const visible = diffs.filter((item) => item.kind !== "UNCHANGED");
  diffList.innerHTML = (visible.length ? visible : diffs.slice(0, 3))
    .map(
      (item) =>
        `<li><span class="diff-chip diff-chip--${item.kind.toLowerCase()}">${item.kind}</span>${escapeText(item.detail)}</li>`,
    )
    .join("");
}

function applyChannelSearch(): void {
  const search = byId<HTMLInputElement>("channel-search")
    .value.trim()
    .toLocaleLowerCase();
  channelList
    .querySelectorAll<HTMLElement>("[data-channel-key]")
    .forEach((row) => {
      row.hidden =
        search.length > 0 &&
        !row.textContent?.toLocaleLowerCase().includes(search);
    });
}

document
  .querySelectorAll<HTMLButtonElement>("[data-panel-target]")
  .forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.panelTarget;
      document
        .querySelectorAll<HTMLButtonElement>("[data-panel-target]")
        .forEach((item) => {
          item.setAttribute("aria-selected", String(item === button));
        });
      document
        .querySelectorAll<HTMLElement>("[data-studio-panel]")
        .forEach((panel) => {
          panel.hidden = panel.dataset.studioPanel !== target;
        });
      byId<HTMLElement>(`panel-${target}`).focus();
    });
  });

byId<HTMLInputElement>("channel-search").addEventListener(
  "input",
  applyChannelSearch,
);

byId<HTMLButtonElement>("add-channel").addEventListener("click", () => {
  const sequence = state.server.channels.length + 1;
  state.server.channels.push({
    key: `local_proposal_${sequence}`,
    name: `新提案頻道 ${sequence}`,
    type: "TEXT",
    parent: state.server.categories[0]?.key ?? "questions",
    topic: "本機新增，匯出前需人工核准。",
    slowmodeSeconds: 0,
    autoArchiveMinutes: 1440,
    enabled: false,
    managedCase: false,
    forumTags: [],
    permissions: {},
  });
  markDirty();
  renderChannels();
  renderDiff();
});

const titleInput = byId<HTMLInputElement>("title-input");
const titleModule = byId<HTMLSelectElement>("title-module");
const titleTag = byId<HTMLInputElement>("title-tag");
const titlePreview = byId<HTMLElement>("title-preview");
function updateTitlePreview(): void {
  titlePreview.textContent = canonicalTitlePreview(
    titleModule.value,
    titleTag.value,
    titleInput.value,
  );
}
[titleInput, titleModule, titleTag].forEach((element) =>
  element.addEventListener("input", updateTitlePreview),
);

byId<HTMLInputElement>("import-file").addEventListener(
  "change",
  async (event) => {
    const input = event.currentTarget;
    if (!(input instanceof HTMLInputElement) || !input.files?.[0]) return;
    importText.value = await input.files[0].text();
    importStatus.textContent = "檔案已載入本機預覽區；尚未檢查或合併。";
  },
);

byId<HTMLButtonElement>("inspect-import").addEventListener("click", () => {
  const result = classifyImport(importKind.value, importText.value);
  importStatus.textContent = result.message;
  importStatus.dataset.tone = result.accepted ? "success" : "error";
});

function markdownExport(): string {
  const lines = [
    "# Config Studio 本機提案摘要",
    "",
    "> 由本機設定台匯出；不是已套用設定。",
    "",
    "## 頻道",
    "",
    ...state.server.channels.map(
      (channel) => `- ${channel.name}（${channel.type} / ${channel.parent}）`,
    ),
    "",
    "## 案件狀態",
    "",
    ...state.workflow.states.map(
      (item) => `- ${item.label}：${item.description}`,
    ),
  ];
  return lines.join("\n");
}

function download(filename: string, content: string, type: string): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

document
  .querySelectorAll<HTMLButtonElement>("[data-export]")
  .forEach((button) => {
    button.addEventListener("click", () => {
      const kind = button.dataset.export;
      if (kind === "json") {
        download(
          "discord-config-proposal.json",
          JSON.stringify(state, null, 2),
          "application/json",
        );
      } else if (kind === "yaml") {
        download(
          "discord-config-proposal.yaml",
          JSON.stringify(state, null, 2),
          "application/yaml",
        );
      } else {
        download(
          "discord-config-summary.md",
          markdownExport(),
          "text/markdown",
        );
      }
    });
  });

renderChannels();
renderDiff();
updateTitlePreview();
