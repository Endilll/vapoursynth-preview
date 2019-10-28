from __future__ import annotations

from   datetime import timedelta
import logging
from   typing   import (
    Any, cast, Dict, Generic, Optional, Type, TYPE_CHECKING, TypeVar, Union,
)

from PyQt5 import Qt

from vspreview.core import (
    Frame, FrameInterval, FrameType, Time, TimeInterval, TimeType, Output,
)
from vspreview.models import SceningList
from vspreview.utils  import debug, from_qtime, to_qtime


# TODO: replace specialized Edit classes with some metaclasses magic or such


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
            self.  verticalScrollBar().setValue(self.  verticalScrollBar().value() - event.angleDelta().y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - event.angleDelta().x())
            return
        elif modifiers == Qt.Qt.ShiftModifier:
            self.  verticalScrollBar().setValue(self.  verticalScrollBar().value() - event.angleDelta().x())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - event.angleDelta().y())
            return

        event.ignore()


T = TypeVar('T', Output, SceningList, float)


class ComboBox(Qt.QComboBox, Generic[T]):
    def __class_getitem__(cls, t: Type[T]) -> Type:
        type_specializations: Dict[Type, Type] = {
            Output     : _ComboBox_Output,
            SceningList: _ComboBox_SceningList,
            float      : _ComboBox_float,
        }

        try:
            return type_specializations[t]
        except KeyError:
            raise TypeError

    indexChanged = Qt.pyqtSignal(int, int)

    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)

        self.type: Type[T]

        self.setSizeAdjustPolicy(Qt.QComboBox.AdjustToMinimumContentsLengthWithIcon)

        self.oldValue = self.currentData()
        self.oldIndex = self.currentIndex()
        self.currentIndexChanged.connect(self._currentIndexChanged)

    def _currentIndexChanged(self, newIndex: int) -> None:
        newValue = self.currentData()
        self.valueChanged.emit(newValue, self.oldValue)
        self.indexChanged.emit(newIndex, self.oldIndex)
        self.oldValue = newValue
        self.oldIndex = newIndex

    def currentValue(self) -> Optional[T]:
        return cast(Optional[T], self.currentData())

    def setCurrentValue(self, newValue: T) -> None:
        i = self.model().index_of(newValue)
        self.setCurrentIndex(i)


class _ComboBox_Output(ComboBox):
    T = Output
    if TYPE_CHECKING:
        valueChanged = Qt.pyqtSignal(T, Optional[T])
    else:
        valueChanged = Qt.pyqtSignal(T, object)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class _ComboBox_SceningList(ComboBox):
    T = SceningList
    if TYPE_CHECKING:
        valueChanged = Qt.pyqtSignal(T, Optional[T])
    else:
        valueChanged = Qt.pyqtSignal(T, object)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class _ComboBox_float(ComboBox):
    T = float
    if TYPE_CHECKING:
        valueChanged = Qt.pyqtSignal(T, Optional[T])
    else:
        valueChanged = Qt.pyqtSignal(T, object)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class FrameEdit(Qt.QSpinBox, Generic[FrameType]):
    def __class_getitem__(cls, t: Type[FrameType]) -> Type:
        type_specializations: Dict[Type, Type] = {
            Frame        : _FrameEdit_Frame,
            FrameInterval: _FrameEdit_FrameInterval,
        }

        try:
            return type_specializations[t]
        except KeyError:
            raise TypeError

    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)

        self.type: Type[FrameType]

        self.setMinimum(self.type(0))

        self.oldValue: FrameType = self.value()
        super().valueChanged.connect(self._valueChanged)

    def _valueChanged(self, newValue: int) -> None:
        self.valueChanged.emit(self.value(), self.oldValue)

    def value(self) -> FrameType:  # type: ignore
        return self.type(super().value())

    def setValue(self, newValue: FrameType) -> None:  # type: ignore
        super().setValue(int(newValue))

    def minimum(self) -> FrameType:  # type: ignore
        return self.type(super().minimum())

    def setMinimum(self, newValue: FrameType) -> None:  # type: ignore
        super().setMinimum(int(newValue))

    def maximum(self) -> FrameType:  # type: ignore
        return self.type(super().maximum())

    def setMaximum(self, newValue: FrameType) -> None:  # type: ignore
        super().setMaximum(int(newValue))


class _FrameEdit_Frame(FrameEdit):
    T = Frame
    valueChanged = Qt.pyqtSignal(T, T)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class _FrameEdit_FrameInterval(FrameEdit):
    T = FrameInterval
    valueChanged = Qt.pyqtSignal(T, T)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class TimeEdit(Qt.QTimeEdit, Generic[TimeType]):
    def __class_getitem__(cls, t: Type[TimeType]) -> Type:
        type_specializations: Dict[Type, Type] = {
            Time        : _TimeEdit_Time,
            TimeInterval: _TimeEdit_TimeInterval,
        }

        try:
            return type_specializations[t]
        except KeyError:
            raise TypeError

    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)

        self.type: Type[TimeType]

        self.setDisplayFormat('H:mm:ss.zzz')
        self.setButtonSymbols(Qt.QTimeEdit.NoButtons)
        self.setMinimum(self.type())

        self.oldValue: TimeType = self.value()
        cast(Qt.pyqtSignal, self.timeChanged).connect(self._timeChanged)

    def _timeChanged(self, newValue: Qt.QTime) -> None:
        self.valueChanged.emit(self.value(), self.oldValue)
        self.oldValue = self.value()

    def value(self) -> TimeType:
        return from_qtime(super().time(), self.type)

    def setValue(self, newValue: TimeType) -> None:
        super().setTime(to_qtime(newValue))

    def minimum(self) -> TimeType:
        return from_qtime(super().minimumTime(), self.type)

    def setMinimum(self, newValue: TimeType) -> None:
        super().setMinimumTime(to_qtime(newValue))

    def maximum(self) -> TimeType:
        return from_qtime(super().maximumTime(), self.type)

    def setMaximum(self, newValue: TimeType) -> None:
        super().setMaximumTime(to_qtime(newValue))


class _TimeEdit_Time(TimeEdit):
    T = Time
    valueChanged = Qt.pyqtSignal(T, T)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class _TimeEdit_TimeInterval(TimeEdit):
    T = TimeInterval
    valueChanged = Qt.pyqtSignal(T, T)

    def __init__(self, *args: Any, **kwargs: Any):
        self.type = self.T
        super().__init__(*args, **kwargs)


class StatusBar(Qt.QStatusBar):
    def __init__(self, parent: Qt.QWidget) -> None:
        super().__init__(parent)

        self.permament_start_index = 0

    def addPermanentWidget(self, widget: Qt.QWidget, stretch: int = 0) -> None:
        self.insertPermanentWidget(self.permament_start_index, widget, stretch)

    def addWidget(self, widget: Qt.QWidget, stretch: int = 0) -> None:
        self.permament_start_index += 1
        super().addWidget(widget, stretch)

    def insertWidget(self, index: int, widget: Qt.QWidget, stretch: int = 0) -> int:
        self.permament_start_index += 1
        return super().insertWidget(index, widget, stretch)
