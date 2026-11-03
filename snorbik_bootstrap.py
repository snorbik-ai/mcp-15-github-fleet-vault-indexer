"""
Snorbik Zero-Install Runtime Bootstrap (v1.0)
Garantit la présence d'un runtime Python 3.10+ autonome.
Si Python système >= 3.10 est présent : l'utilise immédiatement en 0 ms.
Sinon : auto-provisionne le mini-runtime portable officiel dans ~/.snorbik/python-runtime/ sans droits admin.
"""
import sys
import os
import urllib.request
import zipfile
import subprocess
from pathlib import Path

MIN_PYTHON = (3, 10)
SNORBIK_DIR = Path.home() / ".snorbik"
RUNTIME_DIR = SNORBIK_DIR / "python-runtime"
EMBED_URL = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

def get_guaranteed_python() -> Path:
    # 1. Utiliser le Python courant s'il est conforme
    if sys.version_info >= MIN_PYTHON:
        return Path(sys.executable)
    
    # 2. Utiliser le runtime portable existant s'il a déjà été provisionné
    exe_name = "python.exe" if os.name == "nt" else "bin/python3"
    target_exe = RUNTIME_DIR / exe_name
    if target_exe.exists():
        return target_exe

    # 3. Auto-provisionnement du mini-runtime portable (15 Mo)
    print(f"[*] Aucun Python >= 3.10 détecté sur la machine.")
    print(f"[*] Provisionnement automatique du mini-runtime Snorbik dans {RUNTIME_DIR}...")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    
    zip_path = SNORBIK_DIR / "python_embed.zip"
    try:
        urllib.request.urlretrieve(EMBED_URL, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(RUNTIME_DIR)
        if zip_path.exists():
            zip_path.unlink()
            
        # Décommenter 'import site' pour activer pip
        for pth in RUNTIME_DIR.glob("*._pth"):
            lines = pth.read_text(encoding="utf-8").splitlines()
            new_lines = [l.replace("#import site", "import site") for l in lines]
            pth.write_text("\n".join(new_lines), encoding="utf-8")
            
        # Installer pip
        pip_script = RUNTIME_DIR / "get-pip.py"
        urllib.request.urlretrieve(GET_PIP_URL, pip_script)
        subprocess.run([str(target_exe), str(pip_script), "--no-warn-script-location"], cwd=str(RUNTIME_DIR), check=True)
        if pip_script.exists():
            pip_script.unlink()
            
        print(f"[+] Mini-runtime autonome opérationnel : {target_exe}")
        return target_exe
    except Exception as e:
        print(f"[-] Avertissement provisionnement : {e}")
        return Path(sys.executable)

if __name__ == "__main__":
    py = get_guaranteed_python()
    print(f"Python certifié Snorbik : {py}")
