"""Localisation et exécution sécurisées des outils externes (ExifTool, FFmpeg).

Règles de sécurité :
- jamais de shell : les arguments sont passés sous forme de liste ;
- le dossier courant et les entrées relatives du PATH sont ignorés, pour
  qu'un exécutable piégé posé à côté d'un fichier analysé ne soit jamais lancé ;
- sous Windows, seuls les ``.exe`` sont acceptés (les ``.bat``/``.cmd`` passent
  par cmd.exe, dont l'analyse des arguments est exploitable) ;
- chaque appel a un délai maximal.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

# Outils embarqués par l'installeur (prioritaires sur ceux du système).
if getattr(sys, "frozen", False):
    BUNDLED_BIN = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "bin"
else:
    BUNDLED_BIN = Path(__file__).resolve().parents[2] / "bin"


class ToolError(RuntimeError):
    """Un outil externe a échoué ; le message est destiné à l'utilisateur."""


class ToolNotFound(ToolError):
    pass


@lru_cache(maxsize=None)
def find_tool(name: str) -> Path | None:
    exe = f"{name}.exe" if os.name == "nt" else name
    directories = [BUNDLED_BIN]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if entry and os.path.isabs(entry):
            directories.append(Path(entry))
    for directory in directories:
        candidate = directory / exe
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def run_tool(
    name: str,
    args: Sequence[str],
    *,
    stdin: bytes | None = None,
    timeout: float = 120,
) -> subprocess.CompletedProcess[bytes]:
    exe = find_tool(name)
    if exe is None:
        raise ToolNotFound(f"{name} est introuvable. Installez-le ou placez-le dans {BUNDLED_BIN}.")

    extra: dict[str, int] = {}
    if os.name == "nt":
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.run(
            [str(exe), *args],
            input=stdin,
            stdin=None if stdin is not None else subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
            **extra,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{name} : délai dépassé ({timeout:.0f} s).") from exc
    except OSError as exc:
        raise ToolError(f"{name} : lancement impossible ({exc.strerror}).") from exc


def tool_version(name: str) -> str | None:
    """Version lisible de l'outil, ou None s'il est absent ou inutilisable."""
    flag = "-ver" if name == "exiftool" else "-version"
    try:
        proc = run_tool(name, [flag], timeout=10)
    except ToolError:
        return None
    if proc.returncode != 0:
        return None
    first_line = proc.stdout.decode("utf-8", "replace").strip().splitlines()[:1]
    if not first_line:
        return None
    words = first_line[0].split()
    # « ffmpeg version 7.1.1-1 Copyright… » → « 7.1.1-1 »
    if len(words) >= 3 and words[1] == "version":
        return words[2]
    return words[0]


def first_line(raw: bytes, fallback: str) -> str:
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.strip():
            return line.strip()
    return fallback
