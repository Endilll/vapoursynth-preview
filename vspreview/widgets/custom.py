from __future__ import annotations

from   datetime import timedelta
import logging
from   typing   import Optional

from PyQt5 import Qt

from vspreview.utils import debug, qtime_to_timedelta, timedelta_to_qtime


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

        self.setSizeAdjustPolicy(Qt.QComboBox.AdjustToMinimumContentsLengthWithIcon)

    def _indexChanged(self, nextIndex: int) -> None:
        self.indexChanged.emit(nextIndex, self.prevIndex)
        self.prevIndex = nextIndex


class TimeEdit(Qt.QTimeEdit):
    valueChanged = Qt.pyqtSignal(timedelta, timedelta)

    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)

        self.setDisplayFormat('H:mm:ss.zzz')
        self.setButtonSymbols(Qt.QTimeEdit.NoButtons)
        self.setMinimumTime(timedelta())

        self.prevValue = self.time()
        self.timeChanged.connect(self._valueChanged)

    def _valueChanged(self, new_value: Qt.QTime) -> None:
        self.valueChanged.emit(self.time(), self.prevValue)
        self.prevValue = self.time()

    def time(self) -> timedelta:
        return qtime_to_timedelta(super().time())

    def setTime(self, new_value: timedelta) -> None:
        super().setTime(timedelta_to_qtime(new_value))

    def minimumTime(self) -> timedelta:
        return qtime_to_timedelta(super().minimumTime())

    def setMinimumTime(self, new_value: timedelta) -> None:
        super().setMinimumTime(timedelta_to_qtime(new_value))

    def maximumTime(self) -> timedelta:
        return qtime_to_timedelta(super().maximumTime())

    def setMaximumTime(self, new_value: timedelta) -> None:
        super().setMaximumTime(timedelta_to_qtime(new_value))


class StatusBar(Qt.QStatusBar):
    def __init__(self, parent: Qt.QWidget) -> None:
        super().__init__(parent)

        self.permament_start_index = 0

    def addPermanentWidget(self, widget: Qt.QWidget, stretch: int = 0) -> int:
        return self.insertPermanentWidget(self.permament_start_index, widget, stretch)

    def addWidget(self, widget: Qt.QWidget, stretch: int = 0) -> int:
        self.permament_start_index += 1
        return super().addWidget(widget, stretch)

    def insertWidget(self, index: int, widget: Qt.QWidget, stretch: int = 0) -> int:
        self.permament_start_index += 1
        return super().addWidget(index, widget, stretch)
