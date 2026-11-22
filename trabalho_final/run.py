"""
Bootstrap: garante o Python 3.11.9 exato num venv local (.venv), instala o requirements.txt
e executa o programa dentro desse venv. Usa só a biblioteca padrão, então roda com qualquer
Python 3.8+ que você já tenha.

    python run.py                          # abre o front (ENTRY abaixo)
    python run.py leitor_multimetro.py --quality-only     # outro script, com argumentos

Como acha o 3.11.9:
  1. Procura um Python 3.11.9 já instalado (o que está rodando este script ou `py -3.11`).
  2. Se não houver, baixa o 3.11.9 com o `uv` (instalado numa pasta local, .uv_tool). O Python
     do uv já vem com tkinter. Nada é instalado no sistema.
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

TARGET = "3.11.9"
ENTRY = "multimeter_calibration_GUI.py"

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
UV_DIR = ROOT / ".uv_tool"
REQ = ROOT / "requirements.txt"
STAMP = VENV / ".requirements.sha256"


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def version_of(exe) -> str:
    """Versão completa (ex.: 3.11.9) do interpretador, ou '' se não rodar."""
    try:
        out = subprocess.run([str(exe), "-c", "import sys;print('.'.join(map(str,sys.version_info[:3])))"],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def find_installed():
    """Um python 3.11.9 já presente na máquina, ou None."""
    candidates = [sys.executable]
    if os.name == "nt" and shutil.which("py"):
        try:
            out = subprocess.run(["py", "-3.11", "-c", "import sys;print(sys.executable)"],
                                 capture_output=True, text=True, timeout=30)
            if out.returncode == 0 and out.stdout.strip():
                candidates.append(out.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    for c in candidates:
        if version_of(c) == TARGET:
            return c
    return None


def run_uv(*args):
    """Roda o uv (instalando-o em .uv_tool na primeira vez)."""
    if not UV_DIR.exists():
        print("Instalando o uv (só na pasta local .uv_tool)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet",
                               "--target", str(UV_DIR), "uv"])
    env = dict(os.environ, PYTHONPATH=str(UV_DIR) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    subprocess.check_call([sys.executable, "-m", "uv", *args], env=env)


def ensure_venv():
    vp = venv_python()
    if vp.exists() and version_of(vp) == TARGET:
        return
    if VENV.exists():
        print(f"Recriando o .venv (não tem o Python {TARGET}).")
        shutil.rmtree(VENV)
    found = find_installed()
    if found:
        print(f"Criando o .venv com o Python {TARGET} já instalado: {found}")
        subprocess.check_call([found, "-m", "venv", str(VENV)])
    else:
        print(f"Python {TARGET} não encontrado; baixando com o uv (pode demorar um pouco)...")
        run_uv("venv", "--python", TARGET, "--seed", str(VENV))
    if version_of(venv_python()) != TARGET:
        sys.exit(f"Não consegui criar um venv com o Python {TARGET}.")


def ensure_requirements():
    digest = hashlib.sha256(REQ.read_bytes()).hexdigest()
    if STAMP.exists() and STAMP.read_text().strip() == digest:
        return
    print("Instalando as dependências do requirements.txt...")
    subprocess.check_call([str(venv_python()), "-m", "pip", "install", "-r", str(REQ)])
    STAMP.write_text(digest)


def main():
    ensure_venv()
    ensure_requirements()
    args = sys.argv[1:]
    script = args.pop(0) if args and args[0].endswith(".py") else ENTRY
    sys.exit(subprocess.call([str(venv_python()), str(ROOT / script), *args], cwd=ROOT))


if __name__ == "__main__":
    main()
