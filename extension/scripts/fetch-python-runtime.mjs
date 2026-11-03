#!/usr/bin/env node
/**
 * Puts a MINIMUM Python kit inside the VSIX package:
 * - bundled/python-embed/*.zip  (official CPython 3.12 embeddable)
 * - bundled/wheels/*.whl        (pydantic + pydantic_core for offline pip)
 *
 * Runtime is ALWAYS materialized under ~/.snorbik/python-runtime (short path)
 * at Install MCP time — avoids Windows MAX_PATH failures in deep monorepos.
 */
import {
  createWriteStream,
  existsSync,
  mkdirSync,
  readdirSync,
  rmSync,
  unlinkSync,
  writeFileSync,
  copyFileSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import { pipeline } from "node:stream/promises";
import https from "node:https";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const extensionRoot = join(__dirname, "..");
const EMBED_DIR = join(extensionRoot, "bundled", "python-embed");
const WHEELS_DIR = join(extensionRoot, "bundled", "wheels");
const EMBED_NAME = "python-3.12.3-embed-amd64.zip";
const EMBED_URL = `https://www.python.org/ftp/python/3.12.3/${EMBED_NAME}`;
const STAGE = join(homedir(), ".snorbik", "ext-build-python312");

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const follow = (current, left) => {
      https
        .get(current, (res) => {
          if (
            res.statusCode >= 300 &&
            res.statusCode < 400 &&
            res.headers.location &&
            left
          ) {
            follow(res.headers.location, left - 1);
            return;
          }
          if (res.statusCode !== 200) {
            reject(new Error(`HTTP ${res.statusCode} ${url}`));
            return;
          }
          pipeline(res, createWriteStream(dest)).then(resolve).catch(reject);
        })
        .on("error", reject);
    };
    follow(url, 5);
  });
}

function run(exe, args, cwd) {
  const res = spawnSync(exe, args, { encoding: "utf-8", cwd });
  if (res.status !== 0) {
    throw new Error(res.stderr || res.stdout || `exit ${res.status}`);
  }
  return res;
}

async function main() {
  if (process.platform !== "win32") {
    console.log("[*] Non-Windows: skip embed kit (system Python 3.10+).");
    mkdirSync(join(extensionRoot, "bundled"), { recursive: true });
    writeFileSync(
      join(extensionRoot, "bundled", "PYTHON_KIT_README.txt"),
      "Windows VSIX ships python-embed zip + wheels. On macOS/Linux install Python 3.10+.\n",
      "utf-8"
    );
    return;
  }

  mkdirSync(EMBED_DIR, { recursive: true });
  mkdirSync(WHEELS_DIR, { recursive: true });

  const embedZip = join(EMBED_DIR, EMBED_NAME);
  if (!existsSync(embedZip)) {
    console.log(`[*] Fetch embed zip → ${embedZip}`);
    await download(EMBED_URL, embedZip);
  } else {
    console.log(`[+] Embed zip present: ${embedZip}`);
  }

  // Build short-path runtime to download wheels offline into the package.
  if (existsSync(STAGE)) {
    rmSync(STAGE, { recursive: true, force: true });
  }
  mkdirSync(STAGE, { recursive: true });
  const tmpZip = join(homedir(), ".snorbik", "python_embed_tmp.zip");
  copyFileSync(embedZip, tmpZip);
  const ps = spawnSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-Command",
      `Expand-Archive -LiteralPath '${tmpZip.replace(/'/g, "''")}' -DestinationPath '${STAGE.replace(/'/g, "''")}' -Force`,
    ],
    { encoding: "utf-8" }
  );
  if (ps.status !== 0) throw new Error(ps.stderr || ps.stdout);
  try {
    unlinkSync(tmpZip);
  } catch {
    /* ignore */
  }

  for (const name of readdirSync(STAGE)) {
    if (!name.endsWith("._pth")) continue;
    const p = join(STAGE, name);
    const { readFileSync } = await import("node:fs");
    const text = readFileSync(p, "utf-8");
    writeFileSync(p, text.replace(/#\s*import site/, "import site"), "utf-8");
  }

  const exe = join(STAGE, "python.exe");
  const getPip = join(STAGE, "get-pip.py");
  await download("https://bootstrap.pypa.io/get-pip.py", getPip);
  run(exe, [getPip, "--no-warn-script-location"], STAGE);
  // Download wheels into package (offline install later)
  run(
    exe,
    [
      "-m",
      "pip",
      "download",
      "-d",
      WHEELS_DIR,
      "pydantic>=2.7.0",
      "pydantic-core",
      "typing-extensions",
      "annotated-types",
    ],
    STAGE
  );
  run(
    exe,
    [
      "-m",
      "pip",
      "install",
      "--no-warn-script-location",
      "--no-index",
      `--find-links=${WHEELS_DIR}`,
      "pydantic>=2.7.0",
    ],
    STAGE
  );
  const ver = run(exe, ["-c", "import pydantic; print(pydantic.__version__)"]);
  // Keep stage as the live ~/.snorbik/python-runtime for this machine too
  const runtime = join(homedir(), ".snorbik", "python-runtime");
  if (existsSync(runtime)) {
    rmSync(runtime, { recursive: true, force: true });
  }
  const { cpSync } = await import("node:fs");
  cpSync(STAGE, runtime, { recursive: true });
  console.log(`[+] Kit ready. pydantic ${ver.stdout.trim()}`);
  console.log(`[+] Embed: ${embedZip}`);
  console.log(`[+] Wheels: ${WHEELS_DIR} (${readdirSync(WHEELS_DIR).length} files)`);
  console.log(`[+] Live runtime: ${runtime}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
