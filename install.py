#!/usr/bin/env python3
"""Installateur multi-clients — 15-github-fleet-vault-indexer (règle P1 / Article 04 §07)."""
import sys
from snorbik_bootstrap import get_guaranteed_python
PYTHON_BIN = get_guaranteed_python()
import json
import os
import platform
from pathlib import Path

COMPONENT_NAME = "15-github-fleet-vault-indexer"
ENTRYPOINT_REL = "canal_mcp/mcp_server.py"
IS_NODE = False


def _inject(file_path: Path, root_key: str, entry: dict, create_parents: bool = True) -> bool:
    try:
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        elif not file_path.parent.exists():
            return False
        data = {root_key: {}}
        if file_path.exists():
            raw = file_path.read_text(encoding="utf-8").strip()
            if raw:
                data = json.loads(raw)
            if root_key not in data or not isinstance(data[root_key], dict):
                data[root_key] = {}
        data[root_key][COMPONENT_NAME] = entry
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[+] {file_path}")
        return True
    except Exception as exc:
        print(f"[-] {file_path}: {exc}")
        return False


def main() -> int:
    root = Path(__file__).resolve().parent
    entrypoint = (root / ENTRYPOINT_REL).resolve()
    if IS_NODE:
        entry = {"command": "node", "args": [entrypoint.as_posix()], "type": "stdio"}
    else:
        entry = {
            "command": str(PYTHON_BIN),
            "args": [entrypoint.as_posix()],
            "cwd": root.as_posix(),
            "env": {"PYTHONIOENCODING": "utf-8", "PYTHONPATH": root.as_posix()},
            "type": "stdio",
        }
    _inject(Path.home() / ".cursor" / "mcp.json", "mcpServers", entry, True)
    _inject(Path.cwd() / ".vscode" / "mcp.json", "servers", {k: v for k, v in entry.items() if k != "type"}, True)
    if platform.system() == "Windows":
        app = os.environ.get("APPDATA")
        if app:
            _inject(Path(app) / "Claude" / "claude_desktop_config.json", "mcpServers", {k: v for k, v in entry.items() if k != "type"}, False)
    print(f"✅ {COMPONENT_NAME} installé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
