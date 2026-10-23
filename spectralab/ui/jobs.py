"""Exécution des traitements en arrière-plan, sans jamais bloquer l'interface.

Le travail s'exécute dans le pool de threads de Qt ; le résultat revient
toujours dans le thread de l'interface (connexion « queued »), seul
endroit où l'on a le droit de toucher aux widgets.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot

from spectralab.core.tools import ToolError

log = logging.getLogger(__name__)

# Erreurs dont le message est rédigé pour l'utilisateur.
_USER_ERRORS = (ToolError, ValueError, OSError)

_pending: set[_Bridge] = set()


class _Bridge(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, on_success: Callable[[Any], None] | None, on_error: Callable[[str], None] | None) -> None:
        super().__init__()
        self._on_success = on_success
        self._on_error = on_error
        queued = Qt.ConnectionType.QueuedConnection
        self.succeeded.connect(self._deliver_success, queued)
        self.failed.connect(self._deliver_error, queued)

    @Slot(object)
    def _deliver_success(self, result: object) -> None:
        _pending.discard(self)
        if self._on_success:
            self._on_success(result)

    @Slot(str)
    def _deliver_error(self, message: str) -> None:
        _pending.discard(self)
        if self._on_error:
            self._on_error(message)


class _Task(QRunnable):
    def __init__(self, bridge: _Bridge, fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        super().__init__()
        self._bridge = bridge
        self._fn, self._args, self._kwargs = fn, args, kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except _USER_ERRORS as exc:
            self._bridge.failed.emit(str(exc) or exc.__class__.__name__)
        except Exception:
            log.exception("Échec inattendu de %s", getattr(self._fn, "__name__", self._fn))
            self._bridge.failed.emit("Erreur inattendue : consultez le journal pour les détails.")
        else:
            self._bridge.succeeded.emit(result)


def submit(
    fn: Callable[..., Any],
    *args: Any,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    **kwargs: Any,
) -> None:
    """Lance ``fn(*args, **kwargs)`` en arrière-plan. À appeler depuis le thread de l'interface."""
    bridge = _Bridge(on_success, on_error)
    _pending.add(bridge)  # garde le pont en vie jusqu'à la livraison du résultat
    QThreadPool.globalInstance().start(_Task(bridge, fn, args, kwargs))
