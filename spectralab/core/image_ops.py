"""Conversion et redimensionnement d'images (repris de l'ancien main.py)."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from .paths import checked_file, derived_path

MAX_DIMENSION = 20_000

# Libellé → (format Pillow, extension). Ordre = ordre d'affichage.
OUTPUT_FORMATS: dict[str, tuple[str, str]] = {
    "PNG": ("PNG", ".png"),
    "JPEG": ("JPEG", ".jpg"),
    "WEBP": ("WEBP", ".webp"),
    "AVIF": ("AVIF", ".avif"),
    "TIFF": ("TIFF", ".tiff"),
    "GIF": ("GIF", ".gif"),
    "BMP": ("BMP", ".bmp"),
    "ICO": ("ICO", ".ico"),
}
_LOSSY = {"JPEG", "WEBP", "AVIF"}
_NO_ALPHA = {"JPEG", "BMP"}


@dataclass(frozen=True)
class ImageResult:
    path: Path
    size_before: int
    size_after: int
    dimensions: tuple[int, int]


def available_formats() -> list[str]:
    Image.init()
    return [label for label, (fmt, _) in OUTPUT_FORMATS.items() if fmt in Image.SAVE]


@contextmanager
def _open(path: Path) -> Iterator[Image.Image]:
    # Une « bombe de décompression » (image minuscule sur disque, énorme en
    # mémoire) devient une erreur au lieu d'un simple avertissement.
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            image.load()
            yield image


def _prepare(image: Image.Image, fmt: str) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    if fmt in _NO_ALPHA and (image.mode in ("RGBA", "LA") or "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if fmt == "JPEG" and image.mode not in ("RGB", "L", "CMYK"):
        return image.convert("RGB")
    return image


def _save(image: Image.Image, source: Image.Image, dest: Path, fmt: str, quality: int, keep_metadata: bool) -> None:
    params: dict[str, object] = {}
    if fmt in _LOSSY:
        params["quality"] = max(1, min(100, quality))
    if fmt in ("JPEG", "PNG"):
        params["optimize"] = True
    if icc := source.info.get("icc_profile"):
        params["icc_profile"] = icc  # profil couleur : technique, ne révèle rien
    if keep_metadata:
        params["exif"] = image.getexif()
    try:
        image.save(dest, format=fmt, **params)
    except Exception:
        dest.unlink(missing_ok=True)
        raise


def _resolve_format(label: str) -> tuple[str, str]:
    if label not in available_formats():
        raise ValueError(f"Format non pris en charge : {label}.")
    return OUTPUT_FORMATS[label]


def convert_image(src: str | Path, label: str, *, quality: int = 90, keep_metadata: bool = False) -> ImageResult:
    path = checked_file(src)
    fmt, ext = _resolve_format(label)
    dest = derived_path(path, "", ext) if path.suffix.lower() != ext else derived_path(path, "_converti", ext)
    with _open(path) as source:
        image = _prepare(source, fmt)
        _save(image, source, dest, fmt, quality, keep_metadata)
        dimensions = image.size
    return ImageResult(dest, path.stat().st_size, dest.stat().st_size, dimensions)


def resize_image(
    src: str | Path,
    width: int,
    height: int | None = None,
    *,
    quality: int = 92,
    keep_metadata: bool = False,
) -> ImageResult:
    """Redimensionne ; ``height=None`` conserve les proportions."""
    path = checked_file(src)
    if not 1 <= width <= MAX_DIMENSION or (height is not None and not 1 <= height <= MAX_DIMENSION):
        raise ValueError(f"Les dimensions doivent être comprises entre 1 et {MAX_DIMENSION} px.")
    with _open(path) as source:
        fmt = source.format if source.format in (f for f, _ in OUTPUT_FORMATS.values()) else "PNG"
        image = _prepare(source, fmt)
        if height is None:
            height = max(1, round(image.height * width / image.width))
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        ext = path.suffix if fmt == source.format else ".png"
        dest = derived_path(path, f"_{width}x{height}", ext)
        _save(resized, source, dest, fmt, quality, keep_metadata)
    return ImageResult(dest, path.stat().st_size, dest.stat().st_size, (width, height))
