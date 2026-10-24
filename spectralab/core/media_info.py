"""Informations techniques sur un fichier audio ou vidéo (via ffprobe)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from .cancel import CancelToken
from .paths import checked_file
from .tools import ToolError, first_line, run_tool


@dataclass(frozen=True)
class Stream:
    index: int
    kind: str
    codec: str
    details: str
    codec_name: str = ""  # identifiant court de FFmpeg (« h264 », « av1 »…)


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    format_name: str
    duration: float | None
    size: int | None
    bit_rate: int | None
    streams: tuple[Stream, ...]
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def has_video(self) -> bool:
        return any(s.kind == "video" for s in self.streams)


def _number(value: object, kind: type[int] | type[float]) -> int | float | None:
    try:
        number = kind(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    # « nan », « inf » ou une valeur négative ne décrivent aucun média réel.
    return number if math.isfinite(number) and number >= 0 else None


def _frame_rate(raw: object) -> float | None:
    try:
        rate = float(Fraction(str(raw)))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    return rate if math.isfinite(rate) and rate > 0 else None


def _describe(stream: dict[str, object]) -> str:
    kind = stream.get("codec_type")
    parts: list[str] = []
    if kind == "video":
        if stream.get("width") and stream.get("height"):
            parts.append(f"{stream['width']}×{stream['height']}")
        if fps := _frame_rate(stream.get("avg_frame_rate")):
            parts.append(f"{fps:.3g} i/s")
        if stream.get("pix_fmt"):
            parts.append(str(stream["pix_fmt"]))
    elif kind == "audio":
        if rate := _number(stream.get("sample_rate"), int):
            parts.append(f"{rate / 1000:g} kHz")
        if channels := stream.get("channels"):
            layout = stream.get("channel_layout")
            parts.append(f"{channels} canaux" + (f" ({layout})" if layout else ""))
    if bit_rate := _number(stream.get("bit_rate"), int):
        parts.append(format_bitrate(bit_rate))
    return " · ".join(parts)


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def probe(path: str | Path, *, timeout: float = 60, cancel: CancelToken | None = None) -> MediaInfo:
    src = checked_file(path)
    # Le préfixe « file: » empêche FFmpeg d'interpréter un nom de fichier
    # comme un protocole (« concat: », « http: »…).
    proc = run_tool(
        "ffprobe",
        ["-v", "error", "-print_format", "json", "-show_format", "-show_streams", f"file:{src}"],
        timeout=timeout,
        cancel=cancel,
    )
    if proc.returncode != 0:
        raise ToolError(first_line(proc.stderr, "Fichier illisible par FFmpeg."))
    try:
        data = json.loads(proc.stdout.decode("utf-8", "replace"))
    except ValueError as exc:
        raise ToolError("Réponse de ffprobe illisible.") from exc

    # Le contenu décrit un fichier potentiellement piégé : aucune forme n'est supposée.
    data = _dict(data)
    fmt = _dict(data.get("format"))
    raw_streams = data.get("streams")
    streams = tuple(
        Stream(
            index=index if isinstance(index := s.get("index"), int) else i,
            kind=str(s.get("codec_type", "inconnu")),
            codec=str(s.get("codec_long_name") or s.get("codec_name") or "inconnu"),
            details=_describe(s),
            codec_name=str(s.get("codec_name") or ""),
        )
        for i, s in enumerate(map(_dict, raw_streams if isinstance(raw_streams, list) else []))
    )
    tags = {str(k): str(v) for k, v in _dict(fmt.get("tags")).items()}
    return MediaInfo(
        path=src,
        format_name=str(fmt.get("format_long_name") or fmt.get("format_name") or "inconnu"),
        duration=_number(fmt.get("duration"), float),
        size=_number(fmt.get("size"), int),
        bit_rate=_number(fmt.get("bit_rate"), int),
        streams=streams,
        tags=tags,
    )


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def format_size(size: int | None) -> str:
    if size is None:
        return "—"
    value = float(size)
    for unit in ("o", "Ko", "Mo", "Go"):
        if value < 1024 or unit == "Go":
            return f"{value:.0f} {unit}" if unit == "o" else f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024
    return f"{size} o"


def format_bitrate(bit_rate: int | None) -> str:
    if bit_rate is None:
        return "—"
    if bit_rate >= 1_000_000:
        return f"{bit_rate / 1_000_000:.1f} Mb/s".replace(".", ",")
    return f"{bit_rate / 1000:.0f} kb/s"
