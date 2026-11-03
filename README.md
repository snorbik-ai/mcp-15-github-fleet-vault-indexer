# MCP #15 — GitHub Fleet Vault & AI Indexer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-2024--11--05-emerald.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests Passing](https://img.shields.io/badge/tests-6%2F6%20passed-brightgreen.svg)](#tests)

Serveur MCP officiel et SDK universel pour cartographier les flottes de dépôts Git, automatiser la sauvegarde privée du patrimoine logiciel et enrichir les dépôts publics avec des métadonnées sémantiques IA (topics, descriptions) pour leur découvrabilité mondiale.

Conçu pour les agents autonomes, **Cursor IDE**, **Anthropic Claude**, et les ingénieurs DevOps.

## Points Forts & Garanties

- 🛡️ **Sauvegarde Anti-Perte de Patrimoine :** Initialise automatiquement Git, applique un `.gitignore` blindé rejetant les fichiers > 100 Mo, et synchronise vers des dépôts distants GitHub sécurisés.
- 🤖 **Indexation IA & SEO GitHub :** Injecte jusqu'à 20 topics standardisés et des descriptions optimisées pour le référencement auprès des agents et moteurs de recherche d'outils.
- 📊 **Audit de Flotte Déterministe :** Cartographie en un appel l'état de tous les répertoires d'une arborescence (dépôts orphelins, dossiers sans remote, statuts propres ou modifiés).
- ⚡ **Architecture Hybride Tri-Canal Snorbik :**
  1. **Porte 1 (MCP stdio) :** Serveur JSON-RPC 2.0 pour IDE et agents IA (`git_fleet_audit`, `git_patrimoine_backup_private`, `git_ai_seo_index_public`).
  2. **Porte 2 (CLI) :** Commandes terminal pour scripts bash et PowerShell (`python -m canal_sdk_cli.cli audit`).
  3. **Porte 3 (SDK In-Process) :** Façade Python in-memory pour orchestrateurs d'agents (`GitFleetVaultIndexerSDK`).

## Outils Exposés via le Protocole MCP

| Nom de l'outil | Description | Paramètres |
| :--- | :--- | :--- |
| `git_fleet_audit` | Cartographie tous les répertoires sous une racine et classe les projets (Git lié, orphelin local, non-Git). | `base_directory` |
| `git_patrimoine_backup_private` | Initialise Git si absent, applique un `.gitignore` protecteur, crée le repo GitHub privé et pousse le code. | `local_directory`, `org_or_user`, `repo_name` |
| `git_ai_seo_index_public` | Injecte description et tags IA (topics) sur un dépôt GitHub pour maximiser sa visibilité. | `repo_slug`, `description`, `topics` |
| `git_fleet_ping` | Sonde de santé et de réactivité du serveur MCP. | Aucun |

## Installation & Utilisation

### Configuration dans Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "15-github-fleet-vault-indexer": {
      "command": "python",
      "args": [
        "chemin/vers/15_github_fleet_vault_indexer/canal_mcp/mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### Utilisation CLI

```bash
# Auditer une arborescence locale
python canal_sdk_cli/cli.py audit --dir "C:/MesProjets"

# Sauvegarder un projet local orphelin vers GitHub privé
python canal_sdk_cli/cli.py backup --dir "C:/MesProjets/MonOutil" --org snorbik-ai --repo mon-outil-vault

# Injecter l'indexation IA sur un dépôt public
python canal_sdk_cli/cli.py index --repo snorbik-ai/mon-outil --desc "Mon outil MCP" --topics "mcp,agent,python"
```

## Licence

Distribué sous licence **MIT**. Développé avec excellence par le studio **SNORBIK AI**.
