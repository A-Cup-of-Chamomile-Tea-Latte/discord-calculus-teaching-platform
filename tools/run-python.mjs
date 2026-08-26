#!/usr/bin/env node

import { accessSync, constants } from "node:fs";
import { delimiter, dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));

function sharedRepositoryRoot() {
  const result = spawnSync(
    "git",
    ["-C", repositoryRoot, "rev-parse", "--path-format=absolute", "--git-common-dir"],
    { encoding: "utf8", env: process.env },
  );
  if (result.status !== 0) return undefined;

  const commonDirectory = result.stdout.trim();
  return commonDirectory ? dirname(commonDirectory) : undefined;
}

function executableExists(command) {
  if (command.includes("/") || command.includes("\\")) {
    try {
      accessSync(command, constants.X_OK);
      return true;
    } catch {
      return false;
    }
  }

  return (process.env.PATH ?? "")
    .split(delimiter)
    .filter(Boolean)
    .some((directory) => {
      try {
        accessSync(join(directory, command), constants.X_OK);
        return true;
      } catch {
        return false;
      }
    });
}

const sharedRoot = sharedRepositoryRoot();
const candidates = [
  process.env.PYTHON,
  process.env.VIRTUAL_ENV &&
    join(process.env.VIRTUAL_ENV, process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  join(repositoryRoot, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  sharedRoot &&
    join(sharedRoot, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  "python3",
  "python",
].filter((candidate, index, all) => candidate && all.indexOf(candidate) === index);

const executable = candidates.find(executableExists);

if (!executable) {
  console.error(
    "Python was not found. Set PYTHON to an interpreter path or create .venv in the repository root.",
  );
  process.exit(127);
}

const result = spawnSync(executable, process.argv.slice(2), {
  stdio: "inherit",
  env: process.env,
});

if (result.error) {
  console.error(`Failed to start Python at ${executable}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
