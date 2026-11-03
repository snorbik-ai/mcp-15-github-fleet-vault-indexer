import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

export const COMPONENT_NAME = "15-github-fleet-vault-indexer";
export const ENTRYPOINT_REL = path.join("canal_mcp", "mcp_server.py");

export function resolveBundledRoot(extensionPath: string): string {
  const candidates = [
    path.join(extensionPath, "bundled"),
    path.join(extensionPath, ".."),
  ];
  for (const candidate of candidates) {
    const entry = path.join(candidate, ENTRYPOINT_REL);
    if (fs.existsSync(entry)) {
      return candidate;
    }
  }
  throw new Error(
    "MCP runtime introuvable. Lancez npm run bundle-mcp dans extension/."
  );
}

export function resolveEntrypoint(extensionPath: string): string {
  return path.join(resolveBundledRoot(extensionPath), ENTRYPOINT_REL);
}

export function cursorMcpPath(homeDir: string = os.homedir()): string {
  return path.join(homeDir, ".cursor", "mcp.json");
}

export function vscodeMcpPath(workspaceRoot: string): string {
  return path.join(workspaceRoot, ".vscode", "mcp.json");
}

export function claudeDesktopMcpPath(
  appData?: string,
  platform: NodeJS.Platform = process.platform
): string | null {
  if (platform === "win32") {
    const base = appData || process.env.APPDATA;
    if (!base) {
      return null;
    }
    return path.join(base, "Claude", "claude_desktop_config.json");
  }
  if (platform === "darwin") {
    return path.join(
      os.homedir(),
      "Library",
      "Application Support",
      "Claude",
      "claude_desktop_config.json"
    );
  }
  return path.join(os.homedir(), ".config", "Claude", "claude_desktop_config.json");
}
