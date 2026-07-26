import { readFileSync } from "node:fs";

const workflow = readFileSync(
  new URL("../../../.github/workflows/pages.yml", import.meta.url),
  "utf8",
);

const requiredPatterns = [
  /workflow_dispatch:/,
  /deploy:\s*\n\s*description:/,
  /permissions:\s*\n\s*contents: read/,
  /pages: write/,
  /id-token: write/,
  /github\.event_name == 'workflow_dispatch'/,
  /inputs\.deploy == true/,
  /ASTRO_BASE_PATH: \/\$\{\{ github\.event\.repository\.name \}\}/,
  /ASTRO_SITE_URL: https:\/\/\$\{\{ github\.repository_owner \}\}\.github\.io/,
  /actions\/upload-pages-artifact@v5/,
  /path: apps\/portal\/dist/,
  /actions\/deploy-pages@v5/,
];

for (const pattern of requiredPatterns) {
  if (!pattern.test(workflow)) {
    throw new Error(`Pages workflow is missing required pattern: ${pattern}`);
  }
}

if (/\$\{\{\s*secrets\./.test(workflow)) {
  throw new Error("Pages workflow must not reference repository secrets");
}
if (/pull_request_target|schedule:|repository_dispatch:/.test(workflow)) {
  throw new Error("Pages workflow contains an unexpected trigger");
}

console.log(
  "Pages workflow verified: manual deploy gate, least job permissions, no secrets, project-site base, artifact upload",
);
