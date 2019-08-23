from __future__ import annotations

from typing import Any

from PySide2.QtCore    import QObject, Signal
from PySide2.QtWidgets import QGraphicsPixmapItem


class GraphicsItem(QGraphicsPixmapItem):
    class Signaller(QObject):
        about_to_show = Signal()
    @property
    def about_to_show(self) -> Signal:
        return self._signaller.about_to_show

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._signaller = self.Signaller()
        self._visible = True

    @property
    def visible(self) -> bool:
        return self._visible
    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = value

    def show(self) -> None:
        self.visible = True
        self.about_to_show.emit()
        super().show()  # type: ignore

    def hide(self) -> None:
        self.visible = False
        super().hide()  # type: ignore
