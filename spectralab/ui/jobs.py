"""Exécution des traitements en arrière-plan, sans jamais bloquer l'interface.

Le travail s'exécute dans le pool de threads de Qt ; le résultat revient
toujours dans le thread de l'interface (connexion « queued »), seul
endroit où l'on a le droit de toucher aux widgets.

Chaque travail reçoit un jeton d'annulation : ``submit`` le transmet au
traitement (argument ``cancel``) quand celui-ci l'accepte.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot

from spectralab.core.cancel import Cancelled, CancelToken
from spectralab.core.tools import ToolError

log = logging.getLogger(__name__)

# Erreurs dont le message est rédigé pour l'utilisateur.
_USER_ERRORS = (ToolError, ValueError, OSError)

_pending: set[_Bridge] = set()


class _Bridge(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(
        self,
        on_success: Callable[[Any], None] | None,
        on_error: Callable[[str], None] | None,
        on_cancel: Callable[[str], None] | None,
    ) -> None:
        super().__init__()
        self.token = CancelToken()
        self._on_success = on_success
        self._on_error = on_error
        self._on_cancel = on_cancel or on_error
        queued = Qt.ConnectionType.QueuedConnection
        self.succeeded.connect(self._deliver_success, queued)
        self.failed.connect(self._deliver_error, queued)
        self.cancelled.connect(self._deliver_cancel, queued)

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

    @Slot(str)
    def _deliver_cancel(self, message: str) -> None:
        _pending.discard(self)
        if self._on_cancel:
            self._on_cancel(message)


class Job:
    """Poignée sur un travail lancé ; ``cancel()`` peut être appelée à tout moment."""

    def __init__(self, bridge: _Bridge) -> None:
        self._token = bridge.token

    def cancel(self) -> None:
        self._token.cancel()

    @property
    def cancelled(self) -> bool:
        return self._token.cancelled


class _Task(QRunnable):
    def __init__(self, bridge: _Bridge, fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        super().__init__()
        self._bridge = bridge
        self._fn, self._args, self._kwargs = fn, args, kwargs

    def run(self) -> None:
        try:
            self._bridge.token.check()
            result = self._fn(*self._args, **self._kwargs)
        except Cancelled as exc:
            self._bridge.cancelled.emit(str(exc))
        except _USER_ERRORS as exc:
            self._bridge.failed.emit(str(exc) or exc.__class__.__name__)
        except Exception:
            log.exception("Échec inattendu de %s", getattr(self._fn, "__name__", self._fn))
            self._bridge.failed.emit("Erreur inattendue : consultez le journal pour les détails.")
        else:
            self._bridge.succeeded.emit(result)


def _accepts_cancel(fn: Callable[..., Any]) -> bool:
    try:
        return "cancel" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def submit(
    fn: Callable[..., Any],
    *args: Any,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    on_cancel: Callable[[str], None] | None = None,
    **kwargs: Any,
) -> Job:
    """Lance ``fn(*args, **kwargs)`` en arrière-plan. À appeler depuis le thread de l'interface.

    Sans ``on_cancel``, une annulation est signalée à ``on_error``.
    """
    bridge = _Bridge(on_success, on_error, on_cancel)
    if _accepts_cancel(fn):
        kwargs.setdefault("cancel", bridge.token)
    _pending.add(bridge)  # garde le pont en vie jusqu'à la livraison du résultat
    QThreadPool.globalInstance().start(_Task(bridge, fn, args, kwargs))
    return Job(bridge)


def pending_count() -> int:
    """Nombre de traitements lancés dont le résultat n'est pas encore arrivé."""
    return len(_pending)


def cancel_all() -> None:
    """Annule tous les travaux en cours (fermeture de la fenêtre)."""
    for bridge in list(_pending):
        bridge.token.cancel()
