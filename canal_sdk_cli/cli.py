#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI Terminal -- MCP #15 : GitHub Fleet Vault & AI Indexer.

Porte 2 : Utilisation directe en ligne de commande pour scripts bash / powershell.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canal_sdk_cli.sdk import GitFleetVaultIndexerSDK


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP #15 : Superviseur de Patrimoine Git & Indexeur IA")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Commande audit
    audit_p = subparsers.add_parser("audit", help="Audite l'état de sauvegarde de la flotte de projets.")
    audit_p.add_argument("--poles", default=r"C:\Users\ntpar\Dev_IT\Projet_depo\Projet_IA\_NAVIGATION_PAR_POLES", help="Chemin des pôles")
    audit_p.add_argument("--org", default="snorbik-ai", help="Organisation GitHub cible")

    # Commande backup
    backup_p = subparsers.add_parser("backup", help="Sauvegarde un projet local vers GitHub en mode privé.")
    backup_p.add_argument("--path", required=True, help="Chemin du dossier projet")
    backup_p.add_argument("--name", default=None, help="Nom du dépôt GitHub")
    backup_p.add_argument("--org", default="snorbik-ai", help="Organisation GitHub")
    backup_p.add_argument("--public", action="store_true", help="Publier en public au lieu de privé")

    # Commande index
    index_p = subparsers.add_parser("index", help="Indexe un dépôt public pour la recherche sémantique IA.")
    index_p.add_argument("--repo", required=True, help="Nom du dépôt (ex: snorbik-ai/mcp-14)")
    index_p.add_argument("--desc", default=None, help="Description pour les LLMs")
    index_p.add_argument("--topics", default="", help="Topics séparés par des virgules")
    index_p.add_argument("--homepage", default=None, help="URL de démonstration ou vitrine")

    # Commande ping
    subparsers.add_parser("ping", help="Vérifie la réactivité du service.")

    args = parser.parse_args()
    sdk = GitFleetVaultIndexerSDK()

    if args.command == "audit":
        res = sdk.audit_fleet(poles_path=args.poles, org_name=args.org)
        print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))

    elif args.command == "backup":
        res_b = sdk.backup_project(
            project_path=args.path,
            repo_name=args.name,
            org_name=args.org,
            is_private=not args.public,
        )
        print(json.dumps(res_b.model_dump(), indent=2, ensure_ascii=False))

    elif args.command == "index":
        topic_list = [t.strip() for t in args.topics.split(",") if t.strip()]
        res_i = sdk.index_public_repo(
            repo_name=args.repo,
            description=args.desc,
            topics=topic_list,
            homepage=args.homepage,
        )
        print(json.dumps(res_i.model_dump(), indent=2, ensure_ascii=False))

    elif args.command == "ping":
        print(json.dumps(sdk.ping(), indent=2))


if __name__ == "__main__":
    main()
