"""Adaptateur Technique -- MCP #15 : GitHub Fleet Vault & AI Indexer.

Gestion des commandes Git, GitHub CLI (gh) et sécurisation anti-perte.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

PROTECTIVE_GITIGNORE = """# .gitignore Protecteur Snorbik Patrimoine
# Bloque les fichiers > 100 Mo et fichiers confidentiels

*.pt
*.pth
*.bin
*.onnx
*.safetensors
*.ckpt
*.h5
*.mp4
*.mkv
*.avi
*.mov
*.wav
*.mp3
*.zip
*.tar.gz
*.rar
*.7z

node_modules/
.venv/
venv/
env/
__pycache__/
*.pyc
*.pyo

.env
.env.local
.DS_Store
Thumbs.db
"""


class GitFleetAdapter:
    """Adaptateur d'infrastructure pour piloter Git et GitHub CLI en toute sécurité."""

    def __init__(self):
        self._shell = None

    def _get_wscript_shell(self):
        if self._shell is None and os.name == "nt":
            try:
                import win32com.client
                self._shell = win32com.client.Dispatch("WScript.Shell")
            except Exception:
                self._shell = False
        return self._shell

    def resolve_shortcut(self, lnk_path: Path) -> Path:
        """Résout un raccourci Windows .lnk vers son dossier cible réel."""
        sh = self._get_wscript_shell()
        if sh and lnk_path.exists():
            try:
                sc = sh.CreateShortcut(str(lnk_path))
                target = sc.TargetPath
                if target and os.path.exists(target):
                    return Path(target)
            except Exception:
                pass
        return lnk_path.parent

    def run_cmd(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Exécute une commande de manière étanche."""
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    def fetch_github_repos(self, org_name: str = "snorbik-ai") -> Dict[str, Dict[str, Any]]:
        """Récupère l'inventaire distant complet de l'organisation GitHub."""
        cmd = ["gh", "repo", "list", org_name, "--limit", "150", "--json", "name,isPrivate,description,repositoryTopics,url"]
        code, out, _ = self.run_cmd(cmd)
        if code != 0 or not out:
            return {}
        try:
            repos = json.loads(out)
            return {r["name"].lower(): r for r in repos}
        except Exception:
            return {}

    def ensure_protective_gitignore(self, project_path: Path) -> None:
        """Garantit l'existence d'un .gitignore évitant le rejet GitHub (> 100 Mo)."""
        gi_file = project_path / ".gitignore"
        if not gi_file.exists():
            gi_file.write_text(PROTECTIVE_GITIGNORE, encoding="utf-8")
        else:
            content = gi_file.read_text(encoding="utf-8", errors="ignore")
            needed = [l for l in ["*.pt", "*.onnx", "node_modules/", ".venv/", ".env"] if l not in content]
            if needed:
                gi_file.write_text(content + "\n# Protections Snorbik\n" + "\n".join(needed) + "\n", encoding="utf-8")

    def init_local_git_if_needed(self, project_path: Path, branch: str = "main") -> bool:
        """Initialise Git en local avec un premier commit si non existant."""
        git_dir = project_path / ".git"
        if not git_dir.is_dir():
            code, _, _ = self.run_cmd(["git", "init", "-b", branch], project_path)
            if code != 0:
                return False
            self.ensure_protective_gitignore(project_path)
            self.run_cmd(["git", "add", "."], project_path)
            self.run_cmd(["git", "commit", "-m", "feat(init): initialisation securisee snorbik"], project_path)
            return True
        return False

    def get_git_info(self, project_path: Path) -> Tuple[bool, Optional[str], Optional[str], bool]:
        """Retourne (has_git, remote_url, current_branch, is_dirty)."""
        git_dir = project_path / ".git"
        if not git_dir.is_dir():
            return False, None, None, False

        _, remote, _ = self.run_cmd(["git", "remote", "get-url", "origin"], project_path)
        remote_url = remote if remote else None

        _, branch, _ = self.run_cmd(["git", "branch", "--show-current"], project_path)
        current_branch = branch if branch else None

        _, status_out, _ = self.run_cmd(["git", "status", "--porcelain"], project_path)
        is_dirty = len(status_out) > 0

        return True, remote_url, current_branch, is_dirty

    def create_and_push_repo(
        self,
        project_path: Path,
        repo_slug: str,
        org_name: str = "snorbik-ai",
        is_private: bool = True,
        commit_msg: str = "feat(backup): sauvegarde patrimoniale privee snorbik",
    ) -> Tuple[str, str, Optional[str]]:
        """Sauvegarde un projet vers GitHub. Retourne (action, details, repo_url)."""
        self.ensure_protective_gitignore(project_path)
        has_git, remote_url, _, _ = self.get_git_info(project_path)

        if not has_git:
            self.init_local_git_if_needed(project_path)
        else:
            self.run_cmd(["git", "add", "."], project_path)
            self.run_cmd(["git", "commit", "-m", commit_msg], project_path)

        full_repo_name = f"{org_name}/{repo_slug}"

        if remote_url and org_name in remote_url:
            code, _, err = self.run_cmd(["git", "push", "-u", "origin", "main"], project_path)
            if code == 0:
                return "LINKED_AND_PUSHED", f"Push réussi vers {remote_url}", remote_url
            return "ALREADY_CONNECTED", f"Déjà relié mais push warning : {err}", remote_url

        visibility_flag = "--private" if is_private else "--public"
        create_cmd = ["gh", "repo", "create", full_repo_name, visibility_flag, "--source=.", "--remote=origin", "--push"]
        code, out, err = self.run_cmd(create_cmd, project_path)

        if code == 0:
            target_url = f"https://github.com/{full_repo_name}"
            return "CREATED_AND_PUSHED", f"Dépôt créé et sauvegardé avec succès sur {target_url}", target_url

        if "already exists" in (err + out):
            self.run_cmd(["git", "remote", "add", "origin", f"https://github.com/{full_repo_name}.git"], project_path)
            p_code, _, p_err = self.run_cmd(["git", "push", "-u", "origin", "main"], project_path)
            target_url = f"https://github.com/{full_repo_name}"
            if p_code == 0:
                return "LINKED_AND_PUSHED", f"Relié au dépôt existant et poussé sur {target_url}", target_url
            return "ERROR_PUSH", f"Impossible de pousser sur {target_url} : {p_err}", target_url

        return "ERROR_CREATE", f"Erreur gh repo create : {err or out}", None

    def edit_repo_metadata(
        self,
        repo_name: str,
        description: Optional[str] = None,
        topics: Optional[List[str]] = None,
        homepage: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Injecte description, topics et homepage sur GitHub pour indexation IA."""
        cmd = ["gh", "repo", "edit", repo_name]
        if description:
            cmd.extend(["--description", description])
        if homepage:
            cmd.extend(["--homepage", homepage])
        if topics:
            for t in topics:
                cleaned_t = re.sub(r"[^\w-]", "", t.lower().strip())
                if cleaned_t:
                    cmd.extend(["--add-topic", cleaned_t])

        code, out, err = self.run_cmd(cmd)
        if code == 0:
            return True, f"Métadonnées et topics mis à jour pour {repo_name}."
        return False, err or out
