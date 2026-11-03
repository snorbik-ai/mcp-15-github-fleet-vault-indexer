"""Entités et Contrats de Données -- MCP #15 : GitHub Fleet Vault & AI Indexer.

Architecture Clean Code DDD + Pattern MCP Hybride Tri-Canal Snorbik.
"""

from __future__ import annotations

from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OperationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    FAILED = "FAILED"


class ProjectAuditItem(BaseModel):
    pole_or_category: str
    project_name: str
    disk_path: str
    disk_exists: bool
    has_git: bool
    remote_url: Optional[str] = None
    branch: Optional[str] = None
    is_dirty: bool = False
    github_repo_name: Optional[str] = None
    is_private_on_github: Optional[bool] = None
    topics_count: int = 0
    has_description: bool = False
    security_risk_level: str = "NORMAL"  # "CRITICAL_UNBACKED", "NEEDS_TOPICS", "SAFE_PRIVATE", "SAFE_INDEXED"


class FleetAuditResultDto(BaseModel):
    scanned_at: str
    total_projects: int
    projects_with_git: int
    projects_without_git: int
    projects_with_remote: int
    projects_unbacked_local_only: int
    public_repos_count: int
    private_repos_count: int
    public_repos_missing_topics: int
    items: List[ProjectAuditItem]
    duration_ms: float


class BackupRequestDto(BaseModel):
    project_path: str = Field(..., description="Chemin absolu du dossier de projet à sauvegarder.")
    repo_name: Optional[str] = Field(default=None, description="Nom optionnel du dépôt distant GitHub.")
    org_name: str = Field(default="snorbik-ai", description="Organisation ou compte GitHub cible.")
    is_private: bool = Field(default=True, description="Strictement privé par défaut.")
    commit_message: str = Field(default="feat(backup): sauvegarde patrimoniale privee snorbik", description="Message de commit.")


class BackupResultDto(BaseModel):
    project_name: str
    disk_path: str
    action: str  # "CREATED_AND_PUSHED", "LINKED_AND_PUSHED", "ALREADY_CONNECTED", "ERROR"
    repo_url: Optional[str] = None
    visibility: str = "PRIVATE"
    details: str
    duration_ms: float


class IndexingRequestDto(BaseModel):
    repo_name: str = Field(..., description="Nom du dépôt GitHub (ex: snorbik-ai/mcp-14-zip-archive-media-unpacker).")
    description: Optional[str] = Field(default=None, description="Description percutante du rôle pour les LLMs (< 160 car).")
    topics: List[str] = Field(default_factory=list, description="Liste des tags/topics pour l'indexation IA.")
    homepage: Optional[str] = Field(default=None, description="URL optionnelle de documentation ou de site vitrine.")


class IndexingResultDto(BaseModel):
    repo_name: str
    description: Optional[str] = None
    topics_added: List[str]
    homepage: Optional[str] = None
    status: OperationStatus
    details: str
    duration_ms: float


class ToolRequestDto(BaseModel):
    action: str = Field(..., description="Action demandée : audit, backup, index, ping.")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    caller_agent_id: Optional[str] = None


class ToolResponseDto(BaseModel):
    operation_id: str
    action: str
    status: OperationStatus
    payload: Dict[str, Any] = Field(default_factory=dict)
    execution_duration_ms: float
    timestamp: float = Field(default_factory=time.time)
    error_message: Optional[str] = None
