import * as vscode from "vscode";
import {
  commandAuditWorkspace,
  commandGenerateBlueprint,
  commandInstallMcp,
  commandShowStatus,
} from "./commands";

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("mcp-15-github-fleet-vault-indexer.installMcp", () =>
      commandInstallMcp(context)
    ),
    vscode.commands.registerCommand("mcp-15-github-fleet-vault-indexer.auditWorkspace", () =>
      commandAuditWorkspace(context)
    ),
    vscode.commands.registerCommand("mcp-15-github-fleet-vault-indexer.generateBlueprint", () =>
      commandGenerateBlueprint(context)
    ),
    vscode.commands.registerCommand("mcp-15-github-fleet-vault-indexer.showStatus", () =>
      commandShowStatus(context)
    )
  );
}

export function deactivate(): void {
  // no-op
}
