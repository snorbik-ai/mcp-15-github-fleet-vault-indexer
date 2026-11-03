"""Cas d'Usage Métier -- MCP #15 : GitHub Fleet Vault & AI Indexer.

Orchestration de la cartographie, de la sauvegarde privée et de l'indexation IA.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import time
import uuid

from core.domain.entities import (
    BackupRequestDto,
    BackupResultDto,
    FleetAuditResultDto,
    IndexingRequestDto,
    IndexingResultDto,
    OperationStatus,
    ProjectAuditItem,
    ToolRequestDto,
    ToolResponseDto,
)
from core.infrastructure.adapter import GitFleetAdapter


def slugify(text: str) -> str:
    """Transforme un nom en identifiant valide GitHub."""
    cleaned = re.sub(r"[^a-zA-Z0-9\-.]", "-", text.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-.")



class GitFleetUseCase:
    """Orchestrateur patrimonial pour auditer, sauvegarder et indexer."""

    def __init__(self, adapter: GitFleetAdapter):
        self.adapter = adapter

    def audit_fleet(self, poles_root_path: str, org_name: str = "snorbik-ai") -> FleetAuditResultDto:
        """Audite tous les projets locaux d'un répertoire de pôles et les croise avec GitHub."""
        start_time = time.time()
        poles_root = Path(poles_root_path).resolve()
        gh_repos = self.adapter.fetch_github_repos(org_name)

        items: list[ProjectAuditItem] = []

        if poles_root.exists() and poles_root.is_dir():
            for pole_dir in sorted(poles_root.iterdir()):
                if not pole_dir.is_dir() or pole_dir.name.startswith((".", "stitch_")):
                    continue

                for proj_item in sorted(pole_dir.iterdir()):
                    if proj_item.name.startswith(("00_", ".")) or not proj_item.is_dir():
                        continue

                    # Résolution du dossier réel via raccourci
                    lnk = proj_item / "ACCEDER_AU_CODE_SOURCE.lnk"
                    disk_target = self.adapter.resolve_shortcut(lnk) if lnk.exists() else proj_item

                    has_git, remote, branch, is_dirty = self.adapter.get_git_info(disk_target)

                    gh_match = None
                    if remote:
                        slug = remote.rstrip("/").split("/")[-1].replace(".git", "").lower()
                        gh_match = gh_repos.get(slug)

                    if not gh_match:
                        for cand in [disk_target.name.lower(), proj_item.name.lower()]:
                            cand_clean = cand.split(" - ")[-1].strip().lower()
                            if cand_clean in gh_repos:
                                gh_match = gh_repos[cand_clean]
                                break

                    is_priv = gh_match.get("isPrivate") if gh_match else None
                    topics = [t["name"] for t in gh_match.get("repositoryTopics", [])] if gh_match and gh_match.get("repositoryTopics") else []
                    has_desc = bool(gh_match.get("description")) if gh_match else False

                    # Niveau de risque
                    if not remote:
                        risk = "CRITICAL_UNBACKED"
                    elif is_priv is False and len(topics) == 0:
                        risk = "NEEDS_TOPICS"
                    elif is_priv is True:
                        risk = "SAFE_PRIVATE"
                    else:
                        risk = "SAFE_INDEXED"

                    items.append(
                        ProjectAuditItem(
                            pole_or_category=pole_dir.name,
                            project_name=proj_item.name,
                            disk_path=str(disk_target).replace("\\", "/"),
                            disk_exists=disk_target.exists(),
                            has_git=has_git,
                            remote_url=remote,
                            branch=branch,
                            is_dirty=is_dirty,
                            github_repo_name=gh_match["name"] if gh_match else None,
                            is_private_on_github=is_priv,
                            topics_count=len(topics),
                            has_description=has_desc,
                            security_risk_level=risk,
                        )
                    )

        total = len(items)
        with_git = sum(1 for i in items if i.has_git)
        with_remote = sum(1 for i in items if i.remote_url)
        unbacked = total - with_remote
        publics = sum(1 for i in items if i.is_private_on_github is False)
        privates = sum(1 for i in items if i.is_private_on_github is True)
        missing_top = sum(1 for i in items if i.is_private_on_github is False and i.topics_count == 0)

        duration_ms = (time.time() - start_time) * 1000

        return FleetAuditResultDto(
            scanned_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_projects=total,
            projects_with_git=with_git,
            projects_without_git=total - with_git,
            projects_with_remote=with_remote,
            projects_unbacked_local_only=unbacked,
            public_repos_count=publics,
            private_repos_count=privates,
            public_repos_missing_topics=missing_top,
            items=items,
            duration_ms=round(duration_ms, 2),
        )

    def backup_project(self, request: BackupRequestDto) -> BackupResultDto:
        """Sauvegarde un projet vers GitHub en mode strictement privé."""
        start_time = time.time()
        p = Path(request.project_path).resolve()
        if not p.exists() or not p.is_dir():
            raise FileNotFoundError(f"Le dossier source n'existe pas : {request.project_path}")

        slug = request.repo_name or slugify(p.name)
        action, details, url = self.adapter.create_and_push_repo(
            project_path=p,
            repo_slug=slug,
            org_name=request.org_name,
            is_private=request.is_private,
            commit_msg=request.commit_message,
        )
        duration_ms = (time.time() - start_time) * 1000

        return BackupResultDto(
            project_name=p.name,
            disk_path=str(p).replace("\\", "/"),
            action=action,
            repo_url=url,
            visibility="PRIVATE" if request.is_private else "PUBLIC",
            details=details,
            duration_ms=round(duration_ms, 2),
        )

    def index_repo(self, request: IndexingRequestDto) -> IndexingResultDto:
        """Configure description et topics pour visibilité sémantique IA."""
        start_time = time.time()
        ok, msg = self.adapter.edit_repo_metadata(
            repo_name=request.repo_name,
            description=request.description,
            topics=request.topics,
            homepage=request.homepage,
        )
        duration_ms = (time.time() - start_time) * 1000

        return IndexingResultDto(
            repo_name=request.repo_name,
            description=request.description,
            topics_added=request.topics,
            homepage=request.homepage,
            status=OperationStatus.SUCCESS if ok else OperationStatus.FAILED,
            details=msg,
            duration_ms=round(duration_ms, 2),
        )

    def execute(self, request: ToolRequestDto) -> ToolResponseDto:
        """Exécution universelle pour requêtes JSON-RPC MCP."""
        op_id = f"op_{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        try:
            if request.action == "ping":
                duration_ms = (time.time() - start_time) * 1000
                return ToolResponseDto(
                    operation_id=op_id,
                    action="ping",
                    status=OperationStatus.SUCCESS,
                    payload={"status": "pong", "service": "github_fleet_vault_indexer"},
                    execution_duration_ms=round(duration_ms, 2),
                )
            elif request.action == "audit":
                poles = request.parameters.get("poles_path", r"C:\Users\ntpar\Dev_IT\Projet_depo\Projet_IA\_NAVIGATION_PAR_POLES")
                org = request.parameters.get("org_name", "snorbik-ai")
                res_audit = self.audit_fleet(poles, org)
                duration_ms = (time.time() - start_time) * 1000
                return ToolResponseDto(
                    operation_id=op_id,
                    action="audit",
                    status=OperationStatus.SUCCESS,
                    payload=res_audit.model_dump(),
                    execution_duration_ms=round(duration_ms, 2),
                )
            elif request.action == "backup":
                req_b = BackupRequestDto(**request.parameters)
                res_b = self.backup_project(req_b)
                duration_ms = (time.time() - start_time) * 1000
                return ToolResponseDto(
                    operation_id=op_id,
                    action="backup",
                    status=OperationStatus.SUCCESS,
                    payload=res_b.model_dump(),
                    execution_duration_ms=round(duration_ms, 2),
                )
            elif request.action == "index":
                req_i = IndexingRequestDto(**request.parameters)
                res_i = self.index_repo(req_i)
                duration_ms = (time.time() - start_time) * 1000
                return ToolResponseDto(
                    operation_id=op_id,
                    action="index",
                    status=OperationStatus.SUCCESS if res_i.status == OperationStatus.SUCCESS else OperationStatus.WARNING,
                    payload=res_i.model_dump(),
                    execution_duration_ms=round(duration_ms, 2),
                )
            else:
                duration_ms = (time.time() - start_time) * 1000
                return ToolResponseDto(
                    operation_id=op_id,
                    action=request.action,
                    status=OperationStatus.FAILED,
                    payload={},
                    execution_duration_ms=round(duration_ms, 2),
                    error_message=f"Action inconnue : {request.action}",
                )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResponseDto(
                operation_id=op_id,
                action=request.action,
                status=OperationStatus.FAILED,
                payload={},
                execution_duration_ms=round(duration_ms, 2),
                error_message=str(exc),
            )
