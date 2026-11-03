#!/usr/bin/env node
import { cpSync, mkdirSync, rmSync, existsSync, readdirSync } from "node:fs";
import { dirname, join, sep } from "node:path";
import { fileURLToPath } from "node:url";
const __dirname = dirname(fileURLToPath(import.meta.url));
const extensionRoot = join(__dirname, "..");
const toolRoot = join(extensionRoot, "..");
const dest = join(extensionRoot, "bundled");
mkdirSync(dest, { recursive: true });
const parts = ["canal_mcp", "canal_sdk_cli", "core", "snorbik_bootstrap.py"];
for (const name of readdirSync(toolRoot)) {
  if (name.endsWith("_core") && !parts.includes(name)) parts.push(name);
}
for (const part of parts) {
  const src = join(toolRoot, part);
  if (!existsSync(src)) continue;
  const target = join(dest, part);
  if (existsSync(target)) rmSync(target, { recursive: true, force: true });
  cpSync(src, target, {
    recursive: true,
    filter: (p) => !p.includes(`${sep}__pycache__`) && !p.endsWith(".pyc"),
  });
  console.log(`[+] Bundled ${part}`);
}
console.log(`[+] MCP runtime ready at ${dest}`);
