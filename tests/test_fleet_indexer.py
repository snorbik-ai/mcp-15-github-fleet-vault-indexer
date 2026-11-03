"""Tests unitaires certifiant MCP #15 : GitHub Fleet Vault & AI Indexer."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

MCP_ROOT = Path(__file__).resolve().parents[1]
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from core.infrastructure.adapter import GitFleetAdapter
from core.application.usecases import slugify
from canal_sdk_cli.sdk import GitFleetVaultIndexerSDK


def _run_subproc(args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MCP_ROOT)
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(MCP_ROOT),
        env=env,
        check=False,
    )


def test_cli_ping():
    cli_path = MCP_ROOT / "canal_sdk_cli" / "cli.py"
    proc = _run_subproc([sys.executable, str(cli_path), "ping"])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data.get("status") == "pong"


def test_sdk_ping():
    sdk = GitFleetVaultIndexerSDK()
    res = sdk.ping()
    assert res.get("status") == "pong"
    assert res.get("service") == "github_fleet_vault_indexer"


def test_slugify():
    assert slugify("01 - VOX_EXTRACT - Studio Clonage") == "01-vox-extract-studio-clonage"
    assert slugify("Mon Projet IA 2026 !!") == "mon-projet-ia-2026"


def test_protective_gitignore():
    adapter = GitFleetAdapter()
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = Path(tmp_dir)
        adapter.ensure_protective_gitignore(p)
        gi_file = p / ".gitignore"
        assert gi_file.exists()
        content = gi_file.read_text(encoding="utf-8")
        assert "*.pt" in content
        assert "node_modules/" in content
        assert ".env" in content


def test_init_local_git():
    adapter = GitFleetAdapter()
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = Path(tmp_dir)
        (p / "test.txt").write_text("hello", encoding="utf-8")
        created = adapter.init_local_git_if_needed(p)
        assert created is True
        assert (p / ".git").is_dir()
        has_git, _, branch, _ = adapter.get_git_info(p)
        assert has_git is True
        assert branch == "main"


def test_audit_structure():
    adapter = GitFleetAdapter()
    sdk = GitFleetVaultIndexerSDK()
    with tempfile.TemporaryDirectory() as tmp_dir:
        poles = Path(tmp_dir) / "_NAVIGATION_PAR_POLES"
        pole1 = poles / "01_POLE_TEST"
        proj1 = pole1 / "01 - Projet Un"
        proj1.mkdir(parents=True, exist_ok=True)
        (proj1 / "app.py").write_text("print('test')", encoding="utf-8")

        res = sdk.audit_fleet(poles_path=str(poles))
        assert res.total_projects == 1
        assert res.projects_without_git == 1
        assert res.items[0].security_risk_level == "CRITICAL_UNBACKED"
