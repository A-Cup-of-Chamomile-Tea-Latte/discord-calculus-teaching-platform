import { defineConfig } from "astro/config";

function normalizeBase(value) {
  if (!value || value === "/") return "/";
  return `/${value.replace(/^\/+|\/+$/g, "")}`;
}

const base = normalizeBase(process.env.ASTRO_BASE_PATH);
const site = process.env.ASTRO_SITE_URL || undefined;

export default defineConfig({
  output: "static",
  trailingSlash: "always",
  base,
  site,
});
