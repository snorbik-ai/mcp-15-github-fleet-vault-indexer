import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as https from "node:https";
import * as os from "node:os";
import * as path from "node:path";
import { createWriteStream } from "node:fs";
import { pipeline } from "node:stream/promises";
import { resolveBundledRoot } from "./paths";

const EMBED_URL =
  "https://www.python.org/ftp/python/3.12.3/python-3.12.3-embed-amd64.zip";
const EMBED_NAME = "python-3.12.3-embed-amd64.zip";

export type PythonResolveResult = {
  pythonBin: string;
  source: "snorbik_runtime" | "system" | "kit_extracted" | "downloaded";
};

function isWindowsAppsStub(bin: string): boolean {
  return /WindowsApps[\\/]+(py|python)\.exe$/i.test(bin);
}

export function isUsablePython(bin: string): boolean {
  if (!bin || !fs.existsSync(bin)) {
    return false;
  }
  if (isWindowsAppsStub(bin)) {
    return false;
  }
  const res = spawnSync(
    bin,
    ["-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
    { encoding: "utf-8" }
  );
  return res.status === 0;
}

function hasPydantic(bin: string): boolean {
  const res = spawnSync(bin, ["-c", "import pydantic"], { encoding: "utf-8" });
  return res.status === 0;
}

function snorbikRuntimeExe(): string {
  return path.join(os.homedir(), ".snorbik", "python-runtime", "python.exe");
}

function snorbikRuntimeDir(): string {
  return path.join(os.homedir(), ".snorbik", "python-runtime");
}

function downloadFile(url: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const follow = (current: string, redirects: number) => {
      https
        .get(current, (res) => {
          if (
            res.statusCode &&
            res.statusCode >= 300 &&
            res.statusCode < 400 &&
            res.headers.location &&
            redirects > 0
          ) {
            follow(res.headers.location, redirects - 1);
            return;
          }
          if (res.statusCode !== 200) {
            reject(new Error(`Download HTTP ${res.statusCode} for ${url}`));
            return;
          }
          const out = createWriteStream(dest);
          pipeline(res, out).then(resolve).catch(reject);
        })
        .on("error", reject);
    };
    follow(url, 5);
  });
}

function extractZip(zipPath: string, destDir: string): void {
  const ps = spawnSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-Command",
      `Expand-Archive -LiteralPath '${zipPath.replace(/'/g, "''")}' -DestinationPath '${destDir.replace(/'/g, "''")}' -Force`,
    ],
    { encoding: "utf-8" }
  );
  if (ps.status !== 0) {
    throw new Error(ps.stderr || ps.stdout || "Expand-Archive failed");
  }
}

function enableSiteInEmbed(runtimeDir: string): void {
  for (const name of fs.readdirSync(runtimeDir)) {
    if (!name.endsWith("._pth")) continue;
    const pth = path.join(runtimeDir, name);
    const text = fs.readFileSync(pth, "utf-8");
    fs.writeFileSync(
      pth,
      text.replace(/#\s*import site/, "import site"),
      "utf-8"
    );
  }
}

function findKitPaths(extensionPath: string): {
  embedZip: string | null;
  wheelsDir: string | null;
} {
  try {
    const root = resolveBundledRoot(extensionPath);
    const embedZip = path.join(root, "python-embed", EMBED_NAME);
    const wheelsDir = path.join(root, "wheels");
    return {
      embedZip: fs.existsSync(embedZip) ? embedZip : null,
      wheelsDir:
        fs.existsSync(wheelsDir) && fs.readdirSync(wheelsDir).length > 0
          ? wheelsDir
          : null,
    };
  } catch {
    return { embedZip: null, wheelsDir: null };
  }
}

function installPydantic(
  exe: string,
  runtimeDir: string,
  wheelsDir: string | null,
  log?: (m: string) => void
): void {
  if (hasPydantic(exe)) {
    return;
  }
  const getPip = path.join(runtimeDir, "get-pip.py");
  if (!fs.existsSync(path.join(runtimeDir, "Scripts", "pip.exe")) && !fs.existsSync(path.join(runtimeDir, "Lib", "site-packages", "pip"))) {
    log?.("Bootstrapping pip in portable runtime…");
    // get-pip may already be absent; download if needed by caller
  }
  if (wheelsDir) {
    log?.(`Installing pydantic from VSIX wheels: ${wheelsDir}`);
    const deps = spawnSync(
      exe,
      [
        "-m",
        "pip",
        "install",
        "--no-warn-script-location",
        "--no-index",
        `--find-links=${wheelsDir}`,
        "pydantic>=2.7.0",
      ],
      { encoding: "utf-8", cwd: runtimeDir }
    );
    if (deps.status === 0 && hasPydantic(exe)) {
      return;
    }
  }
  const online = spawnSync(
    exe,
    ["-m", "pip", "install", "--no-warn-script-location", "pydantic>=2.7.0"],
    { encoding: "utf-8", cwd: runtimeDir }
  );
  if (online.status !== 0 || !hasPydantic(exe)) {
    throw new Error(
      online.stderr || online.stdout || "Failed to install pydantic into runtime"
    );
  }
}

async function ensurePip(
  exe: string,
  runtimeDir: string,
  log?: (m: string) => void
): Promise<void> {
  const probe = spawnSync(exe, ["-m", "pip", "--version"], { encoding: "utf-8" });
  if (probe.status === 0) {
    return;
  }
  log?.("Downloading get-pip.py…");
  const getPip = path.join(runtimeDir, "get-pip.py");
  await downloadFile("https://bootstrap.pypa.io/get-pip.py", getPip);
  const pip = spawnSync(exe, [getPip, "--no-warn-script-location"], {
    encoding: "utf-8",
    cwd: runtimeDir,
  });
  try {
    fs.unlinkSync(getPip);
  } catch {
    /* ignore */
  }
  if (pip.status !== 0) {
    throw new Error(pip.stderr || pip.stdout || "get-pip failed");
  }
}

export async function materializeSnorbikRuntime(
  extensionPath: string,
  log?: (msg: string) => void
): Promise<string> {
  if (process.platform !== "win32") {
    throw new Error(
      "Portable Python kit is Windows-first in 0.1.x. Install system Python 3.10+."
    );
  }
  const runtimeDir = snorbikRuntimeDir();
  const exe = snorbikRuntimeExe();
  if (isUsablePython(exe) && hasPydantic(exe)) {
    return exe;
  }

  const kit = findKitPaths(extensionPath);
  fs.mkdirSync(runtimeDir, { recursive: true });

  let zipPath = kit.embedZip;
  if (!zipPath) {
    log?.("No VSIX embed zip — downloading official Python embed…");
    zipPath = path.join(os.homedir(), ".snorbik", EMBED_NAME);
    if (!fs.existsSync(zipPath)) {
      await downloadFile(EMBED_URL, zipPath);
    }
  } else {
    log?.(`Using Python kit from VSIX: ${zipPath}`);
  }

  // Clean incomplete runtime
  for (const name of fs.readdirSync(runtimeDir)) {
    fs.rmSync(path.join(runtimeDir, name), { recursive: true, force: true });
  }
  extractZip(zipPath, runtimeDir);
  enableSiteInEmbed(runtimeDir);
  if (!isUsablePython(exe)) {
    throw new Error(`Runtime extracted but unusable: ${exe}`);
  }
  await ensurePip(exe, runtimeDir, log);
  installPydantic(exe, runtimeDir, kit.wheelsDir, log);
  log?.(`Portable Python ready: ${exe}`);
  return exe;
}

function findSystemPython(): string | null {
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
  ];
  for (const candidate of hardcodedWin) {
    if (isUsablePython(candidate)) {
      return candidate;
    }
  }
  const launcher = spawnSync(
    "py",
    ["-3", "-c", "import sys; print(sys.executable)"],
    { encoding: "utf-8" }
  );
  if (launcher.status === 0 && launcher.stdout?.trim()) {
    const resolved = launcher.stdout.trim();
    if (isUsablePython(resolved)) {
      return resolved;
    }
  }
  return null;
}

/**
 * Guarantee Python 3.10+ for MCP (all MCP tools need it):
 * 1) ~/.snorbik/python-runtime (short path, with pydantic)
 * 2) system Python
 * 3) extract kit shipped inside VSIX (python-embed zip + wheels)
 * 4) download embed + install pydantic
 */
export async function ensureGuaranteedPython(
  extensionPath: string,
  log?: (msg: string) => void
): Promise<PythonResolveResult> {
  const snorbik = snorbikRuntimeExe();
  if (isUsablePython(snorbik) && hasPydantic(snorbik)) {
    log?.(`Python from ~/.snorbik runtime: ${snorbik}`);
    return { pythonBin: snorbik, source: "snorbik_runtime" };
  }

  const system = findSystemPython();
  if (system) {
    // System Python usually has/can install pydantic; try import, else continue to kit.
    if (hasPydantic(system)) {
      log?.(`Python from system: ${system}`);
      return { pythonBin: system, source: "system" };
    }
    log?.(`System Python found but pydantic missing — preferring portable kit.`);
  }

  const kit = findKitPaths(extensionPath);
  if (kit.embedZip) {
    const exe = await materializeSnorbikRuntime(extensionPath, log);
    return { pythonBin: exe, source: "kit_extracted" };
  }

  log?.("No VSIX Python kit — downloading portable runtime…");
  const exe = await materializeSnorbikRuntime(extensionPath, log);
  return { pythonBin: exe, source: "downloaded" };
}
