#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serveur MCP JSON-RPC 2.0 / stdio -- github_fleet_vault_indexer.

Porte 1 : Connexion universelle IDE IA (Cursor, Antigravity, Claude Desktop).
Pattern MCP Hybride Tri-Canal Snorbik.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.domain.entities import ToolRequestDto
from core.infrastructure.adapter import GitFleetAdapter
from core.application.usecases import GitFleetUseCase

adapter = GitFleetAdapter()
usecase = GitFleetUseCase(adapter=adapter)

TOOLS_METADATA = [
    {
        "name": "git_fleet_audit",
        "description": "Cartographie tous les projets d'un répertoire de pôles ou de travail, vérifie l'existence Git et croise avec GitHub pour détecter les projets non sauvegardés (risque de perte).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "poles_path": {
                    "type": "string",
                    "default": "C:\\Users\\ntpar\\Dev_IT\\Projet_depo\\Projet_IA\\_NAVIGATION_PAR_POLES",
                    "description": "Chemin du dossier des pôles de navigation."
                },
                "org_name": {
                    "type": "string",
                    "default": "snorbik-ai",
                    "description": "Compte ou organisation GitHub cible."
                }
            }
        }
    },
    {
        "name": "git_patrimoine_backup_private",
        "description": "Sauvegarde un projet local vers GitHub en mode STRICTEMENT PRIVÉ avec initialisation Git, .gitignore protecteur et push origin main.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Chemin absolu du dossier local du projet."},
                "repo_name": {"type": "string", "description": "Nom du dépôt distant GitHub (laissé vide = déduit du dossier)."},
                "org_name": {"type": "string", "default": "snorbik-ai", "description": "Compte GitHub cible."},
                "is_private": {"type": "boolean", "default": True, "description": "Visibilité privée par défaut pour protéger les secrets d'affaires."}
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "git_ai_seo_index_public",
        "description": "Configure la description, les topics/tags stratégiques et l'URL vitrine d'un dépôt public GitHub pour le rendre trouvable par les LLMs et agents IA.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "Nom du dépôt (ex: snorbik-ai/mcp-14-zip-archive-media-unpacker)."},
                "description": {"type": "string", "description": "Description concise (< 160 car) expliquant le rôle à l'IA."},
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags GitHub pour la recherche IA (ex: mcp, ai-agents, cursor-ide)."
                },
                "homepage": {"type": "string", "description": "URL optionnelle du site vitrine ou documentation."}
            },
            "required": ["repo_name"]
        }
    },
    {
        "name": "git_fleet_ping",
        "description": "Vérifie la réactivité et la disponibilité du serveur MCP #15.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "git_fleet_ping":
        req = ToolRequestDto(action="ping", parameters={})
        return usecase.execute(req).model_dump()
    elif tool_name == "git_fleet_audit":
        req = ToolRequestDto(action="audit", parameters=arguments)
        return usecase.execute(req).model_dump()
    elif tool_name == "git_patrimoine_backup_private":
        req = ToolRequestDto(action="backup", parameters=arguments)
        return usecase.execute(req).model_dump()
    elif tool_name == "git_ai_seo_index_public":
        req = ToolRequestDto(action="index", parameters=arguments)
        return usecase.execute(req).model_dump()
    else:
        return {"error": f"Outil inconnu : {tool_name}"}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            if req_id is None:
                continue
            method = req.get("method")

            if method == "tools/list":
                res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_METADATA}}
            elif method == "tools/call":
                params = req.get("params", {})
                t_name = params.get("name")
                t_args = params.get("arguments", {})
                content = handle_tool_call(t_name, t_args)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(content, ensure_ascii=False)}]}
                }
            elif method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "github_fleet_vault_indexer", "version": "1.0.0"},
                        "capabilities": {"tools": {}}
                    }
                }
            else:
                res = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as exc:
            err_res = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
