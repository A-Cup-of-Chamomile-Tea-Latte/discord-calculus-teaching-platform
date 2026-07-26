export function normalizeBase(base: string): string {
  if (!base || base === "/") return "/";
  return `/${base.replace(/^\/+|\/+$/g, "")}/`;
}

export function joinBase(base: string, path: string): string {
  const normalizedBase = normalizeBase(base);
  const normalizedPath = path.replace(/^\/+/, "");
  return normalizedBase === "/"
    ? `/${normalizedPath}`
    : `${normalizedBase}${normalizedPath}`;
}

export function withBase(path: string): string {
  return joinBase(import.meta.env.BASE_URL, path);
}
