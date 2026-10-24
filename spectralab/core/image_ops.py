"""Conversion et redimensionnement d'images (repris de l'ancien main.py)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from .cancel import CancelToken, check
from .paths import checked_file, derived_path, publish, temp_sibling

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


class InvalidImage(ValueError):
    """Image illisible, corrompue ou trop grande ; message destiné à l'utilisateur."""


def available_formats() -> list[str]:
    Image.init()
    return [label for label, (fmt, _) in OUTPUT_FORMATS.items() if fmt in Image.SAVE]


@contextmanager
def _open(path: Path) -> Iterator[Image.Image]:
    too_big = InvalidImage(f"{path.name} : image trop grande pour être traitée sans risque.")
    try:
        image = Image.open(path)
    except Image.DecompressionBombError as exc:
        raise too_big from exc
    except Exception as exc:
        # Les décodeurs de Pillow lèvent des types variés (SyntaxError,
        # struct.error, EOFError…) sur un fichier piégé ou tronqué.
        raise InvalidImage(f"{path.name} : format d'image non reconnu.") from exc
    with image:
        # Une « bombe de décompression » (image minuscule sur disque, énorme en
        # mémoire) est refusée avant le décodage. Pillow se contente d'un
        # avertissement sous le double de cette limite ; le filtre des
        # avertissements étant global, on vérifie nous-mêmes (sûr entre threads).
        limit = Image.MAX_IMAGE_PIXELS
        if limit and image.width * image.height > limit:
            raise too_big
        try:
            image.load()
        except Image.DecompressionBombError as exc:
            raise too_big from exc
        except Exception as exc:
            raise InvalidImage(f"{path.name} : image corrompue ou tronquée.") from exc
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


def _save(
    image: Image.Image,
    source: Image.Image,
    dest: Path,
    fmt: str,
    quality: int,
    keep_metadata: bool,
    cancel: CancelToken | None,
) -> tuple[int, int]:
    """Écrit sous un nom temporaire, vérifie, puis publie. Renvoie les dimensions relues."""
    params: dict[str, object] = {}
    if fmt in _LOSSY:
        params["quality"] = max(1, min(100, quality))
    if fmt in ("JPEG", "PNG"):
        params["optimize"] = True
    if icc := source.info.get("icc_profile"):
        params["icc_profile"] = icc  # profil couleur : technique, ne révèle rien
    if keep_metadata:
        params["exif"] = image.getexif()
    tmp = temp_sibling(dest)
    try:
        image.save(tmp, format=fmt, **params)
        check(cancel)
        size = _verify(tmp, fmt)
        check(cancel)
        publish(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return size


def _verify(path: Path, fmt: str) -> tuple[int, int]:
    """Relit le fichier produit : il doit s'ouvrir, au bon format, et se décoder entièrement."""
    try:
        with Image.open(path) as written:
            written.verify()
        with Image.open(path) as written:
            written.load()
            if written.format != fmt:
                raise InvalidImage(f"Fichier produit au format {written.format} au lieu de {fmt}.")
            return written.size
    except InvalidImage:
        raise
    except Exception as exc:
        raise InvalidImage("Le fichier produit est illisible : il n'a pas été conservé.") from exc


def _resolve_format(label: str) -> tuple[str, str]:
    if label not in available_formats():
        raise ValueError(f"Format non pris en charge : {label}.")
    return OUTPUT_FORMATS[label]


def convert_image(
    src: str | Path,
    label: str,
    *,
    quality: int = 90,
    keep_metadata: bool = False,
    cancel: CancelToken | None = None,
) -> ImageResult:
    path = checked_file(src)
    fmt, ext = _resolve_format(label)
    dest = derived_path(path, "", ext) if path.suffix.lower() != ext else derived_path(path, "_converti", ext)
    check(cancel)
    with _open(path) as source:
        check(cancel)
        image = _prepare(source, fmt)
        dimensions = _save(image, source, dest, fmt, quality, keep_metadata, cancel)
    return ImageResult(dest, path.stat().st_size, dest.stat().st_size, dimensions)


def resize_image(
    src: str | Path,
    width: int,
    height: int | None = None,
    *,
    quality: int = 92,
    keep_metadata: bool = False,
    cancel: CancelToken | None = None,
) -> ImageResult:
    """Redimensionne ; ``height=None`` conserve les proportions."""
    path = checked_file(src)
    if not 1 <= width <= MAX_DIMENSION or (height is not None and not 1 <= height <= MAX_DIMENSION):
        raise ValueError(f"Les dimensions doivent être comprises entre 1 et {MAX_DIMENSION} px.")
    check(cancel)
    with _open(path) as source:
        check(cancel)
        fmt = source.format if source.format in (f for f, _ in OUTPUT_FORMATS.values()) else "PNG"
        image = _prepare(source, fmt)
        if height is None:
            height = max(1, round(image.height * width / image.width))
        if height > MAX_DIMENSION:
            raise ValueError(f"La hauteur obtenue dépasserait {MAX_DIMENSION} px.")
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        check(cancel)
        ext = path.suffix if fmt == source.format else ".png"
        dest = derived_path(path, f"_{width}x{height}", ext)
        dimensions = _save(resized, source, dest, fmt, quality, keep_metadata, cancel)
    return ImageResult(dest, path.stat().st_size, dest.stat().st_size, dimensions)
