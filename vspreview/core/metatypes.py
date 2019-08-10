from __future__ import annotations

from abc    import ABCMeta
from typing import TYPE_CHECKING

from PySide2.QtCore import QObject

if not TYPE_CHECKING:
    from rx import Observable
else:
    from rx.core.typing import Observable


class QABCMeta(ABCMeta, type(QObject)): pass  # type: ignore
class QABC(metaclass=QABCMeta): pass

class QObservable(Observable, QObject, metaclass=QABCMeta): pass  # t
