"""Familles de fichiers reconnues, par extension."""

from __future__ import annotations

from pathlib import Path

IMAGE = frozenset(
    ".jpg .jpeg .png .webp .avif .heic .heif .tif .tiff .gif .bmp .ico .jxl .dng .cr2 .cr3 .nef .arw .orf .rw2 .psd".split()
)
AUDIO = frozenset(".mp3 .wav .flac .ogg .opus .m4a .aac .wma .aiff .aif".split())
VIDEO = frozenset(".mp4 .mov .mkv .webm .avi .m4v .mts .m2ts .3gp .wmv".split())
DOCUMENT = frozenset(".pdf".split())

ALL = IMAGE | AUDIO | VIDEO | DOCUMENT


def kind_of(path: Path) -> str | None:
    ext = path.suffix.lower()
    for name, family in (("image", IMAGE), ("audio", AUDIO), ("video", VIDEO), ("document", DOCUMENT)):
        if ext in family:
            return name
    return None


def dialog_filter(label: str, extensions: frozenset[str]) -> str:
    patterns = " ".join(f"*{e}" for e in sorted(extensions))
    return f"{label} ({patterns})"
