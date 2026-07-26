import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const expectedBase =
  `/${(process.argv[2] ?? "/").replace(/^\/+|\/+$/g, "")}`.replace(/^\/$/, "/");
const normalizedBase = expectedBase === "/" ? "/" : `${expectedBase}/`;
const requiredPages = [
  "index.html",
  "404.html",
  "cases/index.html",
  "cases/C01-7K4M2Q-0702-1000/index.html",
  "join/index.html",
  "ask/index.html",
  "private-support/index.html",
  "guide/index.html",
  "status/index.html",
  "components/index.html",
];

function collectHtmlFiles(directory, prefix = "") {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = `${prefix}${entry.name}`;
    if (entry.isDirectory()) {
      return collectHtmlFiles(join(directory, entry.name), `${relativePath}/`);
    }
    return entry.isFile() && entry.name.endsWith(".html") ? [relativePath] : [];
  });
}

const htmlFiles = collectHtmlFiles(dist).sort();
for (const relativePath of requiredPages) {
  if (!htmlFiles.includes(relativePath)) {
    throw new Error(`missing required page: ${relativePath}`);
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
  for (const [, attribute, reference] of html.matchAll(
    /\b(href|src|action)="([^"]+)"/g,
  )) {
    referenceCount += 1;
    const allowed =
      reference.startsWith(normalizedBase) ||
      reference.startsWith("#") ||
      reference.startsWith("https://") ||
      reference.startsWith("mailto:") ||
      reference.startsWith("data:");
    if (!allowed) {
      throw new Error(
        `${relativePath}: ${attribute} is not base-safe: ${reference}`,
      );
    }
    if (reference.startsWith(normalizedBase)) {
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

console.log(
  `static portal verified: ${htmlFiles.length} generated pages (${requiredPages.length} required), ${referenceCount} base-safe local references, base=${normalizedBase}`,
);
