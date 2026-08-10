import { spawnSync } from "node:child_process";

const host = "127.0.0.1";
const services = [
  {
    label: "Portal",
    workspace: "@calculus/portal",
    port: 4321,
    url: `http://${host}:4321/`,
  },
  {
    label: "Config Studio",
    workspace: "@calculus/config-studio",
    port: 4322,
    url: `http://${host}:4322/`,
  },
];

const started = [];
let stopping = false;

function runAstro(service, args) {
  return spawnSync(
    "npm",
    ["exec", "--workspace", service.workspace, "--", "astro", "dev", ...args],
    {
      env: { ...process.env, NO_COLOR: process.env.NO_COLOR ?? "1" },
      stdio: "inherit",
    },
  );
}

function stop(exitCode = 0) {
  if (stopping) return;
  stopping = true;
  console.log("\nStopping local review servers…");
  for (const service of [...started].reverse()) {
    runAstro(service, ["stop"]);
  }
  process.exit(exitCode);
}

console.log("Calculus teaching project — local fixture review");
console.log("No Discord connection, deployment, token, or real student data is used.");
for (const service of services) {
  console.log(`${service.label}: ${service.url}`);
}
console.log("Fixture case: http://127.0.0.1:4321/cases/C01-7K4M2Q-0702-1000/");
console.log("Proposed config: config/proposed/");
console.log("Press Ctrl+C once to stop both local servers.\n");

for (const service of services) {
  const result = runAstro(service, [
    "--background",
    "--host",
    host,
    "--port",
    String(service.port),
  ]);
  if (result.status !== 0) {
    console.error(`${service.label} failed to start.`);
    stop(result.status ?? 1);
  }
  started.push(service);
}

console.log("\nBoth fixture-only review servers are ready.");
process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));
setInterval(() => {}, 2_147_483_647);
