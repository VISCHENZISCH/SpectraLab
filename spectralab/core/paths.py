"""Choix des chemins de sortie : on n'écrase jamais un fichier existant.

Les fichiers produits sont d'abord écrits sous un nom temporaire, vérifiés,
puis publiés sous leur nom définitif : un traitement interrompu ne laisse
jamais un fichier tronqué portant un nom normal.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

TEMP_MARKER = ".spectralab-"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 10_000):
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Aucun nom libre pour {path.name}.")


def derived_path(src: Path, suffix: str, ext: str | None = None, out_dir: Path | None = None) -> Path:
    """« photo.jpg » + « _clean » → « photo_clean.jpg » (ou « photo_clean (2).jpg »)."""
    extension = src.suffix if ext is None else ext
    return unique_path((out_dir or src.parent) / f"{src.stem}{suffix}{extension}")


def checked_file(path: str | Path) -> Path:
    """Chemin absolu d'un fichier existant.

    Un chemin absolu ne commence jamais par « - » : il ne peut donc pas être
    pris pour une option par les outils en ligne de commande.
    """
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"{resolved.name} n'est pas un fichier.")
    return resolved


def temp_sibling(path: Path) -> Path:
    """Nom temporaire caché, dans le même dossier (donc sur le même disque).

    L'extension est conservée : les outils s'en servent pour choisir le format.
    """
    for _ in range(100):
        candidate = path.with_name(f".{path.stem}{TEMP_MARKER}{secrets.token_hex(4)}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Aucun nom temporaire libre pour {path.name}.")


def publish(tmp: Path, dest: Path) -> None:
    """Renomme ``tmp`` en ``dest`` sans jamais écraser un fichier existant."""
    if os.name == "nt":
        os.rename(tmp, dest)  # échoue d'elle-même si dest existe
        return
    try:
        os.link(tmp, dest)  # création atomique qui échoue si dest existe
    except FileExistsError:
        raise
    except OSError:
        # Systèmes de fichiers sans liens physiques (FAT, exFAT…).
        if dest.exists():
            raise FileExistsError(f"{dest.name} existe déjà.") from None
        os.replace(tmp, dest)
    else:
        tmp.unlink()
