"""Journal d'activité local (compteurs par jour), affiché sur l'accueil.

Seuls des compteurs sont enregistrés : aucun nom ni chemin de fichier.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

KINDS = ("analysis", "clean", "convert")
RETENTION_DAYS = 60


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "SpectraLab"


class ActivityLog:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or data_dir() / "activity.json"
        self._days = self._load()

    def _load(self) -> dict[str, dict[str, int]]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        days: dict[str, dict[str, int]] = {}
        for day, counts in raw.items() if isinstance(raw, dict) else ():
            try:
                date.fromisoformat(day)
            except (TypeError, ValueError):
                continue
            if isinstance(counts, dict):
                days[day] = {
                    k: v for k, v in counts.items() if k in KINDS and isinstance(v, int) and v > 0
                }
        return days

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._days, indent=1, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError as exc:
            log.warning("Journal d'activité non enregistré : %s", exc)

    def record(self, kind: str, count: int = 1, *, today: date | None = None) -> None:
        if kind not in KINDS:
            raise ValueError(f"Activité inconnue : {kind}")
        if count <= 0:
            return
        today = today or date.today()
        bucket = self._days.setdefault(today.isoformat(), {})
        bucket[kind] = bucket.get(kind, 0) + count
        cutoff = (today - timedelta(days=RETENTION_DAYS)).isoformat()
        self._days = {d: c for d, c in self._days.items() if d >= cutoff}
        self._save()

    def last_days(self, n: int = 7, *, today: date | None = None) -> list[tuple[date, dict[str, int]]]:
        today = today or date.today()
        days = [today - timedelta(days=offset) for offset in range(n - 1, -1, -1)]
        return [(d, dict(self._days.get(d.isoformat(), {}))) for d in days]

    def total(self, kind: str, n: int = 7, *, today: date | None = None) -> int:
        return sum(counts.get(kind, 0) for _, counts in self.last_days(n, today=today))
