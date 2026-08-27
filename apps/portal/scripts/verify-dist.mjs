import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const cliArguments = process.argv.slice(2);
const publicMode = cliArguments.includes("--public");
const baseArgument = cliArguments.find((value) => value !== "--public");
const expectedBase =
  `/${(baseArgument ?? "/").replace(/^\/+|\/+$/g, "")}`.replace(/^\/$/, "/");
const normalizedBase = expectedBase === "/" ? "/" : `${expectedBase}/`;
const publicPages = [
  "index.html",
  "404.html",
  "cases/index.html",
  "join/index.html",
  "guide/index.html",
];
const internalPages = [
  "access/index.html",
  "components/index.html",
  "scenarios/index.html",
  "settings/index.html",
  "sqlite-lab/index.html",
  "status/index.html",
  "team/index.html",
  "team/registrations/index.html",
];
const archivedPages = [
  "ask/index.html",
  "discord-guide/index.html",
  "private-support/index.html",
];
const publicApiActions = new Set([
  `${normalizedBase}api/join`,
  `${normalizedBase}api/cases/lookup`,
]);
const requiredPages = publicMode
  ? publicPages
  : [...publicPages, ...internalPages, ...archivedPages];

function collectHtmlFiles(directory, prefix = "") {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = `${prefix}${entry.name}`;
    if (entry.isDirectory()) {
      return collectHtmlFiles(join(directory, entry.name), `${relativePath}/`);
    }
    return entry.isFile() && entry.name.endsWith(".html") ? [relativePath] : [];
  });
}

function collectFiles(directory, prefix = "") {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = `${prefix}${entry.name}`;
    if (entry.isDirectory()) {
      return collectFiles(join(directory, entry.name), `${relativePath}/`);
    }
    return entry.isFile() ? [relativePath] : [];
  });
}

const htmlFiles = collectHtmlFiles(dist).sort();
for (const relativePath of requiredPages) {
  if (!htmlFiles.includes(relativePath)) {
    throw new Error(`missing required page: ${relativePath}`);
  }
}
if (publicMode) {
  for (const relativePath of internalPages) {
    if (htmlFiles.includes(relativePath)) {
      throw new Error(
        `public artifact contains internal page: ${relativePath}`,
      );
    }
  }
  for (const relativePath of archivedPages) {
    if (htmlFiles.includes(relativePath)) {
      throw new Error(
        `public artifact contains archived page: ${relativePath}`,
      );
    }
  }
  for (const relativePath of collectFiles(dist)) {
    const contents = readFileSync(join(dist, relativePath), "utf8");
    if (
      /calculus-local-access|data-local-access|PBKDF2|建立第一位管理員|SQLite 學習實驗室|discord\.com\/channels\/111111111111111111/.test(
        contents,
      )
    ) {
      throw new Error(
        `public artifact contains internal access or tool code: ${relativePath}`,
      );
    }
    if (relativePath.endsWith(".html")) {
      const visibleText = contents
        .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
        .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
        .replace(/<[^>]+>/g, " ");
      if (
        /Reviewer build|reviewer-only|fixture confirmation|低擬真|尚未接線|本機展示|介面驗證|開發工具|technical spike/i.test(
          visibleText,
        )
      ) {
        throw new Error(
          `public artifact contains development or review wording: ${relativePath}`,
        );
      }
    }
  }
  for (const relativePath of ["index.html", "cases/index.html"]) {
    const contents = readFileSync(join(dist, relativePath), "utf8");
    if (!contents.includes("案件查詢服務尚未啟用")) {
      throw new Error(
        `${relativePath}: public lookup must fail closed until its adapter is connected`,
      );
    }
    if (
      /data-case-endpoint="[^"]+"/.test(contents) &&
      (!contents.includes('data-sync-url="false"') ||
        !/<form[^>]*method="post"[^>]*class="case-search-widget__form"/.test(
          contents,
        ))
    ) {
      throw new Error(
        `${relativePath}: connected lookup must keep the Case ID out of the URL`,
      );
    }
  }
} else {
  const sqliteLab = readFileSync(join(dist, "sqlite-lab/index.html"), "utf8");
  for (const requiredText of [
    "SQLite 學習實驗室",
    "先看懂，再操作 SQLite",
    "唯讀查詢",
    "交易（transaction）",
    "可靠工作佇列（reliable queue）",
    "雲端資料驗證關卡",
  ]) {
    if (!sqliteLab.includes(requiredText)) {
      throw new Error(
        `sqlite-lab/index.html: missing learning module ${requiredText}`,
      );
    }
  }
  if (!/data-sqlite-lab/.test(sqliteLab)) {
    throw new Error("sqlite-lab/index.html: missing interactive lab root");
  }
  const accessPage = readFileSync(join(dist, "access/index.html"), "utf8");
  for (const requiredText of [
    "教學團隊登入",
    "建立第一位系統管理員",
    "這個靜態原型不是正式授權邊界",
  ]) {
    if (!accessPage.includes(requiredText)) {
      throw new Error(
        `access/index.html: missing local access notice ${requiredText}`,
      );
    }
  }
}
let referenceCount = 0;
for (const relativePath of htmlFiles) {
  const html = readFileSync(join(dist, relativePath), "utf8");
  if (!html.includes('lang="zh-Hant"'))
    throw new Error(`${relativePath}: missing zh-Hant`);
  if (/223456789012345678|case_private_001/.test(html)) {
    throw new Error(`${relativePath}: leaked an internal fixture identifier`);
  }
  if (/帳號 123|密碼 123|管理員本機預設/.test(html)) {
    throw new Error(`${relativePath}: contains a legacy preset credential`);
  }
  if (
    publicMode &&
    /working projection|VERIFIED_VIEW|source of truth|AI eligibility|Case actions|Task 13|scaffold|fixture confirmation|technical spike|PREVIEW-JOIN-001|建立 Private Support 預覽|網站代為提問/.test(
      html,
    )
  ) {
    throw new Error(`${relativePath}: contains reviewer-only wording`);
  }
  for (const [, attribute, reference] of html.matchAll(
    /\b(href|src|action)="([^"]+)"/g,
  )) {
    referenceCount += 1;
    const approvedApiAction =
      publicMode && attribute === "action" && publicApiActions.has(reference);
    const allowed =
      reference.startsWith(normalizedBase) ||
      approvedApiAction ||
      reference.startsWith("#") ||
      reference.startsWith("https://") ||
      reference.startsWith("mailto:") ||
      reference.startsWith("data:");
    if (!allowed) {
      throw new Error(
        `${relativePath}: ${attribute} is not base-safe: ${reference}`,
      );
    }
    if (reference.startsWith(normalizedBase) && !approvedApiAction) {
      const withoutBase = reference
        .slice(normalizedBase.length)
        .split(/[?#]/, 1)[0];
      const decoded = decodeURIComponent(withoutBase);
      const target = resolve(dist, decoded);
      if (target !== resolve(dist) && !target.startsWith(`${resolve(dist)}/`)) {
        throw new Error(
          `${relativePath}: local reference escapes dist: ${reference}`,
        );
      }
      const targetExists =
        existsSync(target) &&
        (statSync(target).isFile() || existsSync(join(target, "index.html")));
      if (!targetExists) {
        throw new Error(
          `${relativePath}: broken local ${attribute}: ${reference}`,
        );
      }
    }
  }
}

const joinPage = readFileSync(join(dist, "join/index.html"), "utf8");
for (const requiredText of [
  "下載 Discord APP（推薦）",
  "暫時使用網頁版",
  "https://discord.com/download",
  "https://discord.com/app",
]) {
  if (!joinPage.includes(requiredText)) {
    throw new Error(`join/index.html: missing Discord entry ${requiredText}`);
  }
}

console.log(
  `${publicMode ? "public" : "reviewer"} portal verified: ${htmlFiles.length} generated pages (${requiredPages.length} required), ${referenceCount} base-safe local references, base=${normalizedBase}`,
);
