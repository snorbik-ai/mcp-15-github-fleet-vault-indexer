import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { resolveBundledRoot } from "./paths";
import {
  ensureGuaranteedPython,
  isUsablePython,
  type PythonResolveResult,
} from "./pythonRuntime";

/** @deprecated Prefer ensurePythonForExtension — sync detect without auto-download. */
export function detectPython(): string {
  const hardcodedWin = [
    path.join(
      process.env.LOCALAPPDATA || "",
      "Programs",
      "Python",
      "Python312",
      "python.exe"
    ),
    path.join(
      process.env.LOCALAPPDATA || "",
      "Programs",
      "Python",
      "Python311",
      "python.exe"
    ),
    path.join(
      process.env.USERPROFILE || "",
      ".snorbik",
      "python-runtime",
      "python.exe"
    ),
  ];
  for (const candidate of hardcodedWin) {
    if (isUsablePython(candidate)) {
      return candidate;
    }
  }
  throw new Error(
    "Python 3.10+ introuvable. Lancez Install MCP (provisionne le runtime portable) ou installez Python."
  );
}

export async function ensurePythonForExtension(
  extensionPath: string,
  log?: (msg: string) => void
): Promise<PythonResolveResult> {
  return ensureGuaranteedPython(extensionPath, log);
}

export function runCliJson(
  extensionPath: string,
  pythonBin: string,
  args: string[]
): unknown {
  const toolRoot = resolveBundledRoot(extensionPath);
  const cli = path.join(toolRoot, "canal_sdk_cli", "cli.py");
  if (!fs.existsSync(cli)) {
    throw new Error(`CLI introuvable: ${cli}`);
  }
  const res = spawnSync(pythonBin, [cli, ...args], {
    encoding: "utf-8",
    cwd: toolRoot,
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
      PYTHONPATH: toolRoot,
    },
  });
  if (res.status !== 0) {
    throw new Error(
      (res.stderr || res.stdout || `CLI exit ${res.status}`).slice(0, 1200)
    );
  }
  const out = (res.stdout || "").trim();
  return JSON.parse(out);
}

export function auditWorkspaceJson(
  extensionPath: string,
  pythonBin: string,
  targetDir: string
): unknown {
  return runCliJson(extensionPath, pythonBin, [
    "audit",
    "--dir",
    targetDir,
    "--json",
  ]);
}

export function blueprintJson(
  extensionPath: string,
  pythonBin: string,
  filePath: string
): unknown {
  return runCliJson(extensionPath, pythonBin, [
    "blueprint",
    "--file",
    filePath,
    "--json",
  ]);
}
