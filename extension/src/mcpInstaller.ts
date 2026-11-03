import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import {
  COMPONENT_NAME,
  claudeDesktopMcpPath,
  cursorMcpPath,
  resolveEntrypoint,
  vscodeMcpPath,
} from "./paths";

export type ServerEntry = {
  command: string;
  args: string[];
  env?: Record<string, string>;
  type?: string;
  cwd?: string;
};

export type InstallOptions = {
  extensionPath: string;
  pythonBin: string;
  workspaceRoot?: string;
  homeDir?: string;
  appData?: string;
  createClaudeParents?: boolean;
};

export type InstallResult = {
  cursor: boolean;
  vscode: boolean;
  claudeDesktop: boolean;
  claudeCode: boolean | "command_printed";
  entrypoint: string;
  backups: string[];
  messages: string[];
};

function stamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

export function buildServerEntry(
  pythonBin: string,
  entrypoint: string,
  toolRoot: string
): ServerEntry {
  return {
    command: pythonBin,
    args: [entrypoint.replace(/\\/g, "/")],
    cwd: toolRoot.replace(/\\/g, "/"),
    env: {
      PYTHONIOENCODING: "utf-8",
      PYTHONPATH: toolRoot.replace(/\\/g, "/"),
    },
    type: "stdio",
  };
}

export function injectConfig(
  filePath: string,
  rootKey: "mcpServers" | "servers",
  entry: ServerEntry,
  createParents: boolean,
  backups: string[]
): boolean {
  try {
    const parent = path.dirname(filePath);
    if (!fs.existsSync(parent)) {
      if (!createParents) {
        return false;
      }
      fs.mkdirSync(parent, { recursive: true });
    }

    let data: Record<string, unknown> = { [rootKey]: {} };
    if (fs.existsSync(filePath)) {
      const bak = `${filePath}.bak-${stamp()}`;
      fs.copyFileSync(filePath, bak);
      backups.push(bak);
      const raw = fs.readFileSync(filePath, "utf-8").trim();
      if (raw) {
        data = JSON.parse(raw) as Record<string, unknown>;
      }
    }
    if (typeof data[rootKey] !== "object" || data[rootKey] === null) {
      data[rootKey] = {};
    }
    const bucket = data[rootKey] as Record<string, unknown>;
    const stored =
      rootKey === "servers"
        ? Object.fromEntries(
            Object.entries(entry).filter(([k]) => k !== "type")
          )
        : entry;
    bucket[COMPONENT_NAME] = stored;
    fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, "utf-8");
    return true;
  } catch {
    return false;
  }
}

export function tryClaudeCodeAdd(
  pythonBin: string,
  entrypoint: string
): boolean | "command_printed" {
  const cmd = `claude mcp add ${COMPONENT_NAME} "${pythonBin}" "${entrypoint.replace(/\\/g, "/")}"`;
  const which = spawnSync(process.platform === "win32" ? "where" : "which", ["claude"], {
    encoding: "utf-8",
    shell: true,
  });
  if (which.status !== 0) {
    return "command_printed";
  }
  const res = spawnSync(
    "claude",
    ["mcp", "add", COMPONENT_NAME, pythonBin, entrypoint.replace(/\\/g, "/")],
    { encoding: "utf-8", shell: true }
  );
  if (res.status === 0) {
    return true;
  }
  // Fallback: caller shows cmd string via messages
  void cmd;
  return "command_printed";
}

export function installMcpAllClients(options: InstallOptions): InstallResult {
  const backups: string[] = [];
  const messages: string[] = [];
  const entrypoint = resolveEntrypoint(options.extensionPath);
  const toolRoot = path.dirname(path.dirname(entrypoint));
  const entry = buildServerEntry(options.pythonBin, entrypoint, toolRoot);

  const cursorPath = cursorMcpPath(options.homeDir);
  const cursorOk = injectConfig(cursorPath, "mcpServers", entry, true, backups);
  messages.push(
    cursorOk
      ? `Cursor OK: ${cursorPath}`
      : `Cursor FAIL: ${cursorPath}`
  );

  let vscodeOk = false;
  if (options.workspaceRoot) {
    const vscodePath = vscodeMcpPath(options.workspaceRoot);
    vscodeOk = injectConfig(vscodePath, "servers", entry, true, backups);
    messages.push(
      vscodeOk
        ? `VS Code OK: ${vscodePath}`
        : `VS Code FAIL: ${vscodePath}`
    );
  } else {
    messages.push("VS Code skipped (no workspace folder).");
  }

  const claudePath = claudeDesktopMcpPath(options.appData);
  let claudeOk = false;
  if (claudePath) {
    claudeOk = injectConfig(
      claudePath,
      "mcpServers",
      entry,
      options.createClaudeParents === true,
      backups
    );
    messages.push(
      claudeOk
        ? `Claude Desktop OK: ${claudePath}`
        : `Claude Desktop skipped/missing parent: ${claudePath}`
    );
  } else {
    messages.push("Claude Desktop skipped (APPDATA unavailable).");
  }

  const claudeCode = tryClaudeCodeAdd(options.pythonBin, entrypoint);
  if (claudeCode === "command_printed") {
    messages.push(
      `Claude Code CLI: run → claude mcp add ${COMPONENT_NAME} "${options.pythonBin}" "${entrypoint.replace(/\\/g, "/")}"`
    );
  } else {
    messages.push("Claude Code CLI: registered.");
  }

  return {
    cursor: cursorOk,
    vscode: vscodeOk,
    claudeDesktop: claudeOk,
    claudeCode,
    entrypoint,
    backups,
    messages,
  };
}

export function readInstallStatus(options: {
  homeDir?: string;
  workspaceRoot?: string;
  appData?: string;
}): Record<string, boolean> {
  const status: Record<string, boolean> = {
    cursor: false,
    vscode: false,
    claudeDesktop: false,
  };
  try {
    const cursorFile = cursorMcpPath(options.homeDir);
    if (fs.existsSync(cursorFile)) {
      const data = JSON.parse(fs.readFileSync(cursorFile, "utf-8"));
      status.cursor = Boolean(data?.mcpServers?.[COMPONENT_NAME]);
    }
  } catch {
    /* ignore */
  }
  try {
    if (options.workspaceRoot) {
      const vscodeFile = vscodeMcpPath(options.workspaceRoot);
      if (fs.existsSync(vscodeFile)) {
        const data = JSON.parse(fs.readFileSync(vscodeFile, "utf-8"));
        status.vscode = Boolean(data?.servers?.[COMPONENT_NAME]);
      }
    }
  } catch {
    /* ignore */
  }
  try {
    const claudeFile = claudeDesktopMcpPath(options.appData);
    if (claudeFile && fs.existsSync(claudeFile)) {
      const data = JSON.parse(fs.readFileSync(claudeFile, "utf-8"));
      status.claudeDesktop = Boolean(data?.mcpServers?.[COMPONENT_NAME]);
    }
  } catch {
    /* ignore */
  }
  return status;
}
