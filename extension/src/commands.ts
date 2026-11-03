import * as vscode from "vscode";
import { installMcpAllClients, readInstallStatus } from "./mcpInstaller";
import {
  auditWorkspaceJson,
  blueprintJson,
  ensurePythonForExtension,
} from "./pythonRunner";

function output(): vscode.OutputChannel {
  return vscode.window.createOutputChannel("Code Splitter Auditor");
}

export async function commandInstallMcp(
  context: vscode.ExtensionContext
): Promise<void> {
  const channel = output();
  channel.show(true);
  try {
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Code Splitter: préparation Python + install MCP",
      },
      async () => {
        const py = await ensurePythonForExtension(
          context.extensionPath,
          (m) => channel.appendLine(m)
        );
        channel.appendLine(
          `Python source=${py.source} bin=${py.pythonBin}`
        );
        const workspaceRoot =
          vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        const result = installMcpAllClients({
          extensionPath: context.extensionPath,
          pythonBin: py.pythonBin,
          workspaceRoot,
          createClaudeParents: false,
        });
        for (const msg of result.messages) {
          channel.appendLine(msg);
        }
        const okCount = [
          result.cursor,
          result.vscode,
          result.claudeDesktop,
        ].filter(Boolean).length;
        void vscode.window.showInformationMessage(
          `Code Splitter MCP installé (${okCount}/3 configs, Python=${py.source}). Reload Window.`
        );
      }
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    channel.appendLine(`ERROR: ${message}`);
    void vscode.window.showErrorMessage(`Install MCP échoué: ${message}`);
  }
}

export async function commandShowStatus(
  context: vscode.ExtensionContext
): Promise<void> {
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const status = readInstallStatus({ workspaceRoot });
  void vscode.window.showInformationMessage(
    `Code Splitter — Cursor: ${status.cursor ? "OK" : "NON"} | VS Code: ${
      status.vscode ? "OK" : "NON"
    } | Claude Desktop: ${status.claudeDesktop ? "OK" : "NON"} | ext: ${
      context.extension.packageJSON.version
    }`
  );
}

export async function commandAuditWorkspace(
  context: vscode.ExtensionContext
): Promise<void> {
  const channel = output();
  channel.show(true);
  const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!folder) {
    void vscode.window.showWarningMessage("Ouvrez un dossier workspace.");
    return;
  }
  try {
    const py = await ensurePythonForExtension(context.extensionPath, (m) =>
      channel.appendLine(m)
    );
    const report = auditWorkspaceJson(
      context.extensionPath,
      py.pythonBin,
      folder
    ) as {
      total_files_scanned: number;
      warn_count: number;
      critical_count: number;
      heavy_files: Array<{
        status: string;
        line_count: number;
        relative_path: string;
      }>;
    };
    channel.appendLine(JSON.stringify(report, null, 2));
    const picks = (report.heavy_files || []).slice(0, 30).map((f) => ({
      label: `${f.line_count}L  ${f.status}`,
      description: f.relative_path,
    }));
    if (picks.length === 0) {
      void vscode.window.showInformationMessage(
        `Audit OK — ${report.total_files_scanned} fichiers, aucun dépassement.`
      );
      return;
    }
    await vscode.window.showQuickPick(picks, {
      title: `Fichiers lourds (${report.warn_count} alertes, ${report.critical_count} critiques)`,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    channel.appendLine(`ERROR: ${message}`);
    void vscode.window.showErrorMessage(`Audit échoué: ${message}`);
  }
}

export async function commandGenerateBlueprint(
  context: vscode.ExtensionContext
): Promise<void> {
  const channel = output();
  channel.show(true);
  const editor = vscode.window.activeTextEditor;
  let filePath = editor?.document.uri.fsPath;
  if (!filePath) {
    const uri = await vscode.window.showOpenDialog({
      canSelectMany: false,
      openLabel: "Choisir le fichier à découper",
    });
    filePath = uri?.[0]?.fsPath;
  }
  if (!filePath) {
    return;
  }
  try {
    const py = await ensurePythonForExtension(context.extensionPath, (m) =>
      channel.appendLine(m)
    );
    const plan = blueprintJson(
      context.extensionPath,
      py.pythonBin,
      filePath
    ) as Record<string, unknown>;
    const text = JSON.stringify(plan, null, 2);
    channel.appendLine(text);
    const copy = await vscode.window.showInformationMessage(
      `Blueprint généré pour ${filePath}`,
      "Copier JSON"
    );
    if (copy === "Copier JSON") {
      await vscode.env.clipboard.writeText(text);
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    channel.appendLine(`ERROR: ${message}`);
    void vscode.window.showErrorMessage(`Blueprint échoué: ${message}`);
  }
}
