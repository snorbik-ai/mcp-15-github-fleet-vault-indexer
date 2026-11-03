"""SDK In-Process -- MCP #15 : GitHub Fleet Vault & AI Indexer.

Porte 3 : Accès direct in-memory pour scripts Python et orchestrateurs.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.domain.entities import (
    BackupRequestDto,
    BackupResultDto,
    FleetAuditResultDto,
    IndexingRequestDto,
    IndexingResultDto,
    ToolRequestDto,
    ToolResponseDto,
)
from core.infrastructure.adapter import GitFleetAdapter
from core.application.usecases import GitFleetUseCase


class GitFleetVaultIndexerSDK:
    """Façade Python in-process utilisable directement sans surcoût de sous-processus."""

    def __init__(self):
        self.adapter = GitFleetAdapter()
        self.usecase = GitFleetUseCase(adapter=self.adapter)

    def audit_fleet(
        self,
        poles_path: str = r"C:\Users\ntpar\Dev_IT\Projet_depo\Projet_IA\_NAVIGATION_PAR_POLES",
        org_name: str = "snorbik-ai",
    ) -> FleetAuditResultDto:
        """Audite l'état de sauvegarde de tous les projets locaux."""
        return self.usecase.audit_fleet(poles_root_path=poles_path, org_name=org_name)

    def backup_project(
        self,
        project_path: str,
        repo_name: Optional[str] = None,
        org_name: str = "snorbik-ai",
        is_private: bool = True,
        commit_message: str = "feat(backup): sauvegarde patrimoniale privee snorbik",
    ) -> BackupResultDto:
        """Sauvegarde un projet vers GitHub en mode strictement privé."""
        req = BackupRequestDto(
            project_path=project_path,
            repo_name=repo_name,
            org_name=org_name,
            is_private=is_private,
            commit_message=commit_message,
        )
        return self.usecase.backup_project(req)

    def index_public_repo(
        self,
        repo_name: str,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None,
        homepage: Optional[str] = None,
    ) -> IndexingResultDto:
        """Indexe un dépôt public pour les moteurs IA."""
        req = IndexingRequestDto(
            repo_name=repo_name,
            description=description,
            topics=topics or [],
            homepage=homepage,
        )
        return self.usecase.index_repo(req)

    def execute(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> ToolResponseDto:
        """Point d'entrée générique."""
        req = ToolRequestDto(action=action, parameters=parameters or {})
        return self.usecase.execute(req)

    def ping(self) -> Dict[str, Any]:
        return self.execute("ping").payload
