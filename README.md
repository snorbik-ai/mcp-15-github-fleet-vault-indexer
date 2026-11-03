# MCP #15 — GitHub Fleet Vault & AI Indexer

**Pattern :** MCP Hybride Tri-Canal Snorbik  
**Rôle :** Cartographie de flottes de dépôts, prévention des pertes de code via sauvegarde privée GitHub, et injection de métadonnées sémantiques (topics, descriptions) pour l'indexation IA.

## Portes d'Accès
- **Porte 1 (IDE IA) :** `python canal_mcp/mcp_server.py`
- **Porte 2 (CLI) :** `python canal_sdk_cli/cli.py audit` / `python canal_sdk_cli/cli.py backup`
- **Porte 3 (In-Process) :** `from outils_internes.15_github_fleet_vault_indexer.canal_sdk_cli.sdk import GitFleetVaultIndexerSDK`

## Outils Exposés
1. `git_fleet_audit` : Détecte les projets locaux non reliés au Cloud GitHub.
2. `git_patrimoine_backup_private` : Initialise Git, applique le `.gitignore` protecteur (>100 Mo) et publie en privé.
3. `git_ai_seo_index_public` : Injecte description et tags IA sur les dépôts publics.
4. `git_fleet_ping` : Sonde de réactivité du service.
