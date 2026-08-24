import { existsSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const internalRoutes = [
  "access",
  "ask",
  "components",
  "discord-guide",
  "private-support",
  "scenarios",
  "settings",
  "sqlite-lab",
  "status",
  "team",
];

const internalPageTrees = [];

function htmlFiles(directory) {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = join(directory, entry.name);
    if (entry.isDirectory()) return htmlFiles(target);
    return entry.isFile() && entry.name.endsWith(".html") ? [target] : [];
  });
}

function referencedAssets(files) {
  const assets = new Set();
  for (const file of files) {
    const html = readFileSync(file, "utf8");
    for (const match of html.matchAll(
      /\b(?:href|src)="[^"]*_astro\/([^"?#]+)/g,
    )) {
      assets.add(decodeURIComponent(match[1]));
    }
  }
  return assets;
}

const internalHtml = [...internalRoutes, ...internalPageTrees].flatMap(
  (route) => htmlFiles(join(dist, route)),
);
const allHtml = htmlFiles(dist);
const internalHtmlSet = new Set(internalHtml);
const publicHtml = allHtml.filter((file) => !internalHtmlSet.has(file));
const internalAssets = referencedAssets(internalHtml);
const publicAssets = referencedAssets(publicHtml);

for (const route of internalRoutes) {
  const target = join(dist, route);
  if (existsSync(target)) rmSync(target, { recursive: true, force: true });
}

for (const route of internalPageTrees) {
  const target = join(dist, route);
  if (existsSync(target)) rmSync(target, { recursive: true, force: true });
}

for (const asset of internalAssets) {
  if (publicAssets.has(asset)) continue;
  const target = join(dist, "_astro", asset);
  if (existsSync(target)) rmSync(target, { force: true });
}

console.log(
  `public artifact prepared: removed ${internalRoutes.length + internalPageTrees.length} internal route trees and ${[...internalAssets].filter((asset) => !publicAssets.has(asset)).length} internal-only assets`,
);
