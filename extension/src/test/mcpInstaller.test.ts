import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { test } from "node:test";
import {
  buildServerEntry,
  injectConfig,
  installMcpAllClients,
} from "../mcpInstaller";
import { COMPONENT_NAME } from "../paths";

test("injectConfig Cursor uses mcpServers and keeps peers", () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "cs-cursor-"));
  const file = path.join(home, ".cursor", "mcp.json");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(
    file,
    JSON.stringify({ mcpServers: { Toolbox: { url: "https://x" } } }, null, 2)
  );
  const backups: string[] = [];
  const entry = buildServerEntry("python", "/tmp/mcp_server.py", "/tmp/tool");
  const ok = injectConfig(file, "mcpServers", entry, true, backups);
  assert.equal(ok, true);
  const data = JSON.parse(fs.readFileSync(file, "utf-8"));
  assert.ok(data.mcpServers.Toolbox);
  assert.ok(data.mcpServers[COMPONENT_NAME]);
  assert.equal(backups.length, 1);
});

test("injectConfig VS Code uses servers and forbids mcpServers key pollution", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cs-vscode-"));
  const file = path.join(root, ".vscode", "mcp.json");
  const backups: string[] = [];
  const entry = buildServerEntry("python", "/tmp/mcp_server.py", "/tmp/tool");
  const ok = injectConfig(file, "servers", entry, true, backups);
  assert.equal(ok, true);
  const data = JSON.parse(fs.readFileSync(file, "utf-8"));
  assert.ok(data.servers);
  assert.equal("mcpServers" in data, false);
  assert.ok(data.servers[COMPONENT_NAME]);
  assert.equal(data.servers[COMPONENT_NAME].type, undefined);
});

test("installMcpAllClients writes Cursor + VS Code in sandbox", () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "cs-home-"));
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), "cs-ws-"));
  const extensionPath = path.resolve(__dirname, "..", "..");
  const result = installMcpAllClients({
    extensionPath,
    pythonBin: "python",
    workspaceRoot: workspace,
    homeDir: home,
    appData: path.join(home, "AppData"),
    createClaudeParents: true,
  });
  assert.equal(result.cursor, true);
  assert.equal(result.vscode, true);
  const cursorData = JSON.parse(
    fs.readFileSync(path.join(home, ".cursor", "mcp.json"), "utf-8")
  );
  assert.ok(cursorData.mcpServers[COMPONENT_NAME]);
  const vscodeData = JSON.parse(
    fs.readFileSync(path.join(workspace, ".vscode", "mcp.json"), "utf-8")
  );
  assert.ok(vscodeData.servers[COMPONENT_NAME]);
  assert.equal("mcpServers" in vscodeData, false);
});
