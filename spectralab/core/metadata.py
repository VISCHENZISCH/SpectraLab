"""Lecture, écriture et suppression des métadonnées avec ExifTool.

Les arguments sont transmis à ExifTool par l'entrée standard (``-@ -``) et
non par la ligne de commande : les noms de fichiers et valeurs non ASCII
passent correctement sous Windows, et aucune valeur ne peut être
interprétée comme une option.

Toute écriture passe par un fichier temporaire relu par ExifTool avant de
prendre sa place : l'original n'est remplacé que par un fichier vérifié.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .cancel import CancelToken, check
from .paths import checked_file, derived_path, publish, temp_sibling
from .tools import ToolError, first_line, run_tool

# Groupes décrivant le fichier sur le disque ou calculés par ExifTool :
# ils ne sont pas stockés dans le média et ne peuvent pas être nettoyés.
NON_EMBEDDED_GROUPS = frozenset({"ExifTool", "System", "File", "Composite"})

# « Artist », « XMP-dc:Creator »… Pas de « < », « + » ni « - » final :
# ils changeraient l'opération (copie depuis un fichier, ajout, retrait).
_TAG_RE = re.compile(r"(?:[A-Za-z][A-Za-z0-9-]{0,31}:)?[A-Za-z][A-Za-z0-9_]{0,63}")
_FORBIDDEN_CHARS = re.compile(r"[\x00\r\n]")


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass(frozen=True)
class Entry:
    group: str
    tag: str
    value: str

    @property
    def embedded(self) -> bool:
        return self.group not in NON_EMBEDDED_GROUPS


@dataclass(frozen=True)
class Finding:
    label: str
    severity: Severity
    entries: tuple[Entry, ...]


@dataclass(frozen=True)
class FileMetadata:
    path: Path
    entries: tuple[Entry, ...]
    error: str | None = None

    @property
    def embedded(self) -> list[Entry]:
        return [e for e in self.entries if e.embedded]

    def findings(self) -> list[Finding]:
        return privacy_findings(self.entries)


_RULES: tuple[tuple[str, Severity, re.Pattern[str]], ...] = (
    ("Position GPS", Severity.HIGH, re.compile(r"^GPS|Location|Coordinates", re.I)),
    ("Numéro de série d'appareil", Severity.HIGH, re.compile(r"Serial", re.I)),
    (
        "Identité de l'auteur",
        Severity.MEDIUM,
        re.compile(r"^(Artist|Author|Creator|OwnerName|CameraOwnerName|By-?line|LastModifiedBy|XPAuthor)$", re.I),
    ),
    (
        "Miniature intégrée",
        Severity.MEDIUM,
        re.compile(r"^(ThumbnailImage|PreviewImage|JpgFromRaw|OtherImage)$", re.I),
    ),
    (
        "Appareil et logiciel",
        Severity.LOW,
        re.compile(r"^(Make|Model|LensMake|LensModel|Software|HostComputer|CreatorTool|Encoder|EncodedBy)$", re.I),
    ),
    (
        "Dates de création",
        Severity.LOW,
        re.compile(r"^(DateTimeOriginal|CreateDate|ModifyDate|DateCreated|MetadataDate|CreationDate)$", re.I),
    ),
    (
        "Commentaires et descriptions",
        Severity.LOW,
        re.compile(r"^(Comment|UserComment|XPComment|ImageDescription|Description|Title)$", re.I),
    ),
)


def _classify(entry: Entry) -> tuple[str, Severity] | None:
    if entry.group == "GPS":
        return _RULES[0][0], _RULES[0][1]
    for label, severity, pattern in _RULES:
        if pattern.search(entry.tag):
            return label, severity
    return None


def privacy_findings(entries: Iterable[Entry]) -> list[Finding]:
    grouped: dict[tuple[str, Severity], list[Entry]] = {}
    for entry in entries:
        if entry.embedded and (rule := _classify(entry)):
            grouped.setdefault(rule, []).append(entry)
    findings = [Finding(label, severity, tuple(items)) for (label, severity), items in grouped.items()]
    return sorted(findings, key=lambda f: (-f.severity, f.label))


def risk_level(findings: Iterable[Finding]) -> Severity | None:
    return max((f.severity for f in findings), default=None)


def validate_tag(tag: str) -> str:
    tag = tag.strip()
    if not _TAG_RE.fullmatch(tag):
        raise ValueError(f"Nom de champ invalide : « {tag} ».")
    return tag


def _exiftool(args: list[str], timeout: float, cancel: CancelToken | None = None) -> tuple[int, bytes, bytes]:
    for arg in args:
        if _FORBIDDEN_CHARS.search(arg):
            raise ValueError("Les retours à la ligne et caractères nuls ne sont pas acceptés.")
    payload = ("\n".join(args) + "\n").encode("utf-8")
    proc = run_tool(
        "exiftool",
        ["-charset", "filename=utf8", "-@", "-"],
        stdin=payload,
        timeout=timeout,
        cancel=cancel,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _stringify(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(_stringify(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _same_file_key(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def read_metadata(
    paths: Iterable[str | Path],
    *,
    timeout: float = 120,
    cancel: CancelToken | None = None,
) -> list[FileMetadata]:
    """Lit les métadonnées de plusieurs fichiers en un seul appel à ExifTool."""
    files = [checked_file(p) for p in paths]
    if not files:
        return []
    _, stdout, stderr = _exiftool(["-json", "-G1", "-a", "-s", *map(str, files)], timeout, cancel)
    try:
        records = json.loads(stdout.decode("utf-8", "replace") or "[]")
    except ValueError as exc:
        raise ToolError("Réponse d'ExifTool illisible.") from exc

    by_file: dict[str, dict[str, object]] = {}
    for record in records if isinstance(records, list) else []:
        if isinstance(record, dict) and isinstance(record.get("SourceFile"), str):
            by_file[_same_file_key(record.pop("SourceFile"))] = record

    results = []
    for path in files:
        record = by_file.get(_same_file_key(path))
        if record is None:
            results.append(FileMetadata(path, (), first_line(stderr, "Lecture impossible.")))
            continue
        error = record.pop("ExifTool:Error", None)
        entries = []
        for key, value in record.items():
            group, _, tag = str(key).rpartition(":")
            entries.append(Entry(group, tag, _stringify(value)))
        results.append(FileMetadata(path, tuple(entries), str(error) if error else None))
    return results


def _file_type(meta: FileMetadata) -> str | None:
    return next((e.value for e in meta.entries if e.tag == "FileType"), None)


def _verify(src: Path, written: Path, timeout: float, cancel: CancelToken | None) -> None:
    """Le fichier produit doit être lisible par ExifTool et du même type que la source."""
    if not written.is_file() or written.stat().st_size == 0:
        raise ToolError("ExifTool n'a produit aucun fichier.")
    before, after = read_metadata([src, written], timeout=timeout, cancel=cancel)
    if after.error:
        raise ToolError(f"Le fichier produit est invalide : {after.error}")
    if _file_type(before) != _file_type(after):
        raise ToolError("Le fichier produit n'a plus le même type que l'original.")


def _write(
    args: list[str],
    src: Path,
    output: Path | None,
    timeout: float,
    cancel: CancelToken | None,
) -> Path:
    """Écrit dans un fichier temporaire, le vérifie, puis le publie.

    ``output=None`` remplace l'original, mais seulement une fois la copie
    vérifiée ; sinon ``output`` ne doit pas exister et ne sera jamais écrasé.
    """
    target = src if output is None else Path(output).resolve()
    if output is not None and target.exists():
        raise FileExistsError(f"{target.name} existe déjà.")
    tmp = temp_sibling(target)
    try:
        code, stdout, stderr = _exiftool([*args, "-o", str(tmp), str(src)], timeout, cancel)
        summary = stdout.decode("utf-8", "replace")
        if code != 0 or "weren't updated" in summary or "weren't created" in summary:
            raise ToolError(first_line(stderr, first_line(stdout, "ExifTool n'a pas pu écrire le fichier.")))
        _verify(src, tmp, timeout, cancel)
        check(cancel)
        if output is None:
            os.replace(tmp, src)
        else:
            publish(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def strip_metadata(
    path: str | Path,
    *,
    output: Path | None = None,
    keep_technical: bool = True,
    timeout: float = 300,
    cancel: CancelToken | None = None,
) -> Path:
    """Supprime les métadonnées. ``output=None`` modifie l'original.

    ``keep_technical`` conserve l'orientation et le profil couleur, qui
    ne révèlent rien mais changent le rendu de l'image s'ils disparaissent.
    """
    src = checked_file(path)
    args = ["-all="]
    if keep_technical:
        args += ["-tagsFromFile", "@", "-ColorSpaceTags", "-Orientation"]
    return _write(args, src, output, timeout, cancel)


def clean_copy(path: str | Path, *, keep_technical: bool = True, cancel: CancelToken | None = None) -> Path:
    src = checked_file(path)
    return strip_metadata(src, output=derived_path(src, "_clean"), keep_technical=keep_technical, cancel=cancel)


def write_tags(
    path: str | Path,
    tags: Mapping[str, str],
    *,
    output: Path | None = None,
    timeout: float = 120,
    cancel: CancelToken | None = None,
) -> Path:
    """Écrit des champs. Une valeur vide supprime le champ."""
    if not tags:
        raise ValueError("Aucun champ à écrire.")
    src = checked_file(path)
    args = [f"-{validate_tag(tag)}={value}" for tag, value in tags.items()]
    return _write(args, src, output, timeout, cancel)
