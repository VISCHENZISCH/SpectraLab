"""Choix des chemins de sortie : on n'écrase jamais un fichier existant."""

from __future__ import annotations

from pathlib import Path


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
