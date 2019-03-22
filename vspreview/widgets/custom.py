from __future__ import annotations

import logging
from   typing import Optional

from PyQt5 import Qt

from vspreview.utils import debug


class GraphicsView(Qt.QGraphicsView):
    WHEEL_STEP = 15 * 8  # degrees

    __slots__ = (
        'app', 'angleRemainder'
    )

    wheelScrolled = Qt.pyqtSignal(int)

    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)

        self.app = Qt.QApplication.instance()
        self.angleRemainder = 0

    def setZoom(self, value: int) -> None:
        transform = Qt.QTransform()
        transform.scale(value, value)
        self.setTransform(transform)

    def wheelEvent(self, event: Qt.QWheelEvent) -> None:
        modifiers = self.app.keyboardModifiers()
        if modifiers == Qt.Qt.ControlModifier:
            angleDelta = event.angleDelta().y()

            # check if wheel wasn't rotated the other way since last rotation
            if self.angleRemainder * angleDelta < 0:
                self.angleRemainder = 0

            self.angleRemainder += angleDelta
            if abs(self.angleRemainder) >= self.WHEEL_STEP:
                self.wheelScrolled.emit(self.angleRemainder // self.WHEEL_STEP)
                self.angleRemainder %= self.WHEEL_STEP
            return
        elif modifiers == Qt.Qt.NoModifier:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - event.angleDelta().y())
            return
        elif modifiers == Qt.Qt.ShiftModifier:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - event.angleDelta().y())
            return

        event.ignore()


class ComboBox(Qt.QComboBox):
    indexChanged = Qt.pyqtSignal(int, int)

    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)

        self.prevIndex = self.currentIndex()
        self.currentIndexChanged.connect(self._indexChanged)

    def _indexChanged(self, nextIndex: int) -> None:
        self.indexChanged.emit(nextIndex, self.prevIndex)
        self.prevIndex = nextIndex
