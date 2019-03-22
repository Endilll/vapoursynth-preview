from __future__ import annotations

from   datetime import timedelta
# import logging
from   typing   import Any, cast, Dict, Iterator, List, Optional, Tuple, Union

from PyQt5 import Qt

from vspreview.core import AbstractToolbar, Frame, Scene
# import debug

# pylint: disable=attribute-defined-outside-init

# TODO: add frame mode
# TODO: store cursor pos as frame
# TODO: consider moving from ints to floats


class Notch:
    def __init__(self, data: Union[Frame, timedelta], color: Qt.QColor = cast(Qt.QColor, Qt.Qt.white),
                 label: str = '', line: Qt.QLineF = Qt.QLineF()) -> None:
        self.data  = data
        self.color = color
        self.label = label
        self.line  = line


class Notches:
    def __init__(self, other: Optional[Notches] = None) -> None:
        self.items: List[Notch] = []

        if other is None:
            return
        self.items = other.items

    def add(self, data: Union[Frame, Scene, timedelta, Notch], color: Qt.QColor = cast(Qt.QColor, Qt.Qt.white), label: str = '') -> None:
        if isinstance(data, Notch):
            self.items.append(data)
        elif isinstance(data, Scene):
            if label == '':
                label = data.label
            self.items.append(Notch(data.start, color, label))
            if data.end != data.start:
                self.items.append(Notch(data.end, color, label))
        elif isinstance(data, (Frame, timedelta)):
            self.items.append(Notch(data, color, label))
        else:
            raise TypeError

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> Notch:
        return self.items[index]

    def __iter__(self) -> Iterator[Notch]:
        return iter(self.items)


class Timeline(Qt.QWidget):
    __slots__ = (
        'app', 'main',
        'rectF', 'prevRectF',
        'totalT', 'totalF',
        'notchIntervalTargetX', 'notchHeight', 'fontHeight',
        'notchLabelInterval', 'notchScrollInterval', 'scrollHeight',
        'cursorX', 'cursorFT', 'needFullRepaint',
        'scrollRect',
    )

    clicked = Qt.pyqtSignal(Frame, timedelta)

    def __init__(self, parent: Qt.QWidget) -> None:
        from vspreview.utils import main_window

        super().__init__(parent)
        self.app  = Qt.QApplication.instance()
        self.main = main_window()

        self.rectF  = Qt.QRectF()

        self.totalT = timedelta(seconds=1)
        self.totalF = Frame(1)

        self.notchIntervalTargetX = round(50 * self.main.display_scale)
        self.notchHeight          = round( 6 * self.main.display_scale)
        self.fontHeight           = round(10 * self.main.display_scale)
        self.notchLabelInterval   = round(-1 * self.main.display_scale)
        self.notchScrollInterval  = round( 2 * self.main.display_scale)
        self.scrollHeight         = round(10 * self.main.display_scale)

        self.setMinimumSize(self.notchIntervalTargetX, round(33 * self.main.display_scale))

        font = self.font()
        font.setPixelSize(self.fontHeight)
        self.setFont(font)

        self.cursorX = 0
        # used as a fallback when self.rectF.width() is 0, so cursorX is incorrect
        self.cursorFT: Optional[Union[Frame, timedelta]] = None
        # False means that only cursor position'll be recalculated
        self.needFullRepaint = True

        self.toolbars_notches: Dict[AbstractToolbar, Notches] = {}

        self.setAttribute(Qt.Qt.WA_OpaquePaintEvent)
        self.setMouseTracking(True)

    def paintEvent(self, event: Qt.QPaintEvent) -> None:
        super().paintEvent(event)
        self.rectF = Qt.QRectF(event.rect())
        # self.rectF.adjust(0, 0, -1, -1)

        if self.cursorFT is not None:
            self.setPosition(self.cursorFT)
        self.cursorFT = None

        painter = Qt.QPainter()
        painter.begin(self)
        self.drawWidget(painter)
        painter.end()

    def drawWidget(self, painter: Qt.QPainter) -> None:
        from vspreview.utils import strfdelta

        # calculations

        if self.needFullRepaint:
            notchIntervalT = self.calculateNotchInterval(self.notchIntervalTargetX)
            labelFormat = self.generateLabelFormat(notchIntervalT)

            labelsNotches = Notches()
            labelNotchBottom = self.rectF.top() + self.fontHeight + self.notchLabelInterval + self.notchHeight + 5
            labelNotchTop    = labelNotchBottom - self.notchHeight

            labelNotchX = self.rectF.left()
            labelNotchT = timedelta(0)
            while (labelNotchX < self.rectF.right() and labelNotchT < self.totalT):
                line = Qt.QLineF(labelNotchX, labelNotchBottom, labelNotchX, labelNotchTop)
                labelsNotches.add(Notch(labelNotchT, line=line))
                # notches.append(Notch(line, labelNotchT))
                labelNotchT += notchIntervalT
                labelNotchX  = self.tToX(labelNotchT)

            self.scrollRect = Qt.QRectF(self.rectF.left(), labelNotchBottom + self.notchScrollInterval, self.rectF.width(), self.scrollHeight)

            for toolbar, notches in self.toolbars_notches.items():
                if not toolbar.is_notches_visible():
                    continue

                for notch in notches:
                    if   isinstance(notch.data, Frame):
                        x = self.fToX(notch.data)
                    elif isinstance(notch.data, timedelta):
                        x = self.tToX(notch.data)

                    y = self.scrollRect.top()
                    notch.line = Qt.QLineF(x, y, x, y + self.scrollRect.height() - 1)

        cursorLine = Qt.QLineF(self.cursorX, self.scrollRect.top(), self.cursorX, self.scrollRect.top() + self.scrollRect.height() - 1)

        # drawing

        if self.needFullRepaint:
            painter.fillRect(self.rectF, self.palette().color(Qt.QPalette.Window))

            painter.setPen(Qt.QPen(self.palette().color(Qt.QPalette.WindowText)))
            painter.setRenderHint(Qt.QPainter.Antialiasing, False)
            painter.drawLines([notch.line for notch in labelsNotches])

            painter.setRenderHint(Qt.QPainter.Antialiasing)
            for i in range(0, len(labelsNotches)):
                line = labelsNotches[i].line
                t    = cast(timedelta, labelsNotches[i].data)
                anchorRect = Qt.QRectF(line.x2(), line.y2() - self.notchLabelInterval, 0, 0)
                label = strfdelta(t, labelFormat)
                if   i == 0:
                    rect = painter.boundingRect(anchorRect, Qt.Qt.AlignBottom + Qt.Qt.AlignLeft,    label)
                    rect.moveLeft(-2.5)
                elif i == (len(labelsNotches) - 1):
                    rect = painter.boundingRect(anchorRect, Qt.Qt.AlignBottom + Qt.Qt.AlignHCenter, label)
                    if rect.right() > self.rectF.right():
                        rect = painter.boundingRect(anchorRect, Qt.Qt.AlignBottom + Qt.Qt.AlignRight, label)
                else:
                    rect = painter.boundingRect(anchorRect, Qt.Qt.AlignBottom + Qt.Qt.AlignHCenter, label)
                painter.drawText(rect, label)

        painter.setRenderHint(Qt.QPainter.Antialiasing, False)
        painter.fillRect(self.scrollRect, Qt.Qt.gray)

        for toolbar, notches in self.toolbars_notches.items():
            if not toolbar.is_notches_visible():
                continue

            for notch in notches:
                painter.setPen(notch.color)
                painter.drawLine(notch.line)

        painter.setPen(Qt.Qt.black)
        painter.drawLine(cursorLine)

        self.needFullRepaint = False

    def moveEvent(self, event: Qt.QMoveEvent) -> None:
        super().moveEvent(event)
        self.update()

    def mousePressEvent(self, event: Qt.QMouseEvent) -> None:
        super().mousePressEvent(event)
        pos = Qt.QPoint(event.pos())
        if self.scrollRect.contains(pos):
            self.cursorX = pos.x()
            self.clicked.emit(self.xToF(self.cursorX), self.xToT(self.cursorX))
            self.update()

    def mouseMoveEvent(self, event: Qt.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        for toolbar, notches in self.toolbars_notches.items():
            if not toolbar.is_notches_visible():
                continue
            for notch in notches:
                line = notch.line
                if line.x1() - 0.5 <= event.x() <= line.x1() + 0.5:
                    Qt.QToolTip.showText(event.globalPos(), notch.label)
                    return

    def resizeEvent(self, event: Qt.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update()

    def event(self, event: Qt.QEvent) -> bool:
        if (event.type() == Qt.QEvent.Polish):
            self.setPalette(self.main.palette())
            self.update()
            return True

        return super().event(event)

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.needFullRepaint = True
        super().update(*args, **kwargs)

    def updateNotches(self, toolbar: Optional[AbstractToolbar] = None) -> None:
        if toolbar is not None:
            self.toolbars_notches[toolbar] = toolbar.get_notches()
        if toolbar is None:
            for t in self.main.toolbars:
                self.toolbars_notches[t] = t.get_notches()
        self.update()


    def calculateNotchInterval(self, targetIntervalX: int) -> timedelta:
        # 1.2 means that it's allowed to reduce target interval betweewn labels by 20% at most
        MARGIN = 1.2

        seconds = self.xToT(targetIntervalX).total_seconds()
        if   seconds < 10 * MARGIN:
            notchIntervalT = timedelta(seconds= 10)
        elif seconds < 30 * MARGIN:
            notchIntervalT = timedelta(seconds= 30)
        elif seconds < 60 * MARGIN:
            notchIntervalT = timedelta(seconds= 60)
        else:
            notchIntervalT = timedelta(seconds=120)

        return notchIntervalT

    def generateLabelFormat(self, notchIntervalT: timedelta) -> str:
        if   notchIntervalT >= timedelta(hours=1):
            return '%h:%M'
        elif notchIntervalT >= timedelta(minutes=1):
            return '%m:00'
        else:
            return '%m:%S'

    def setDuration(self, totalF: Frame, totalT: timedelta) -> None:
        self.totalF = totalF
        self.totalT = totalT
        self.needFullRepaint = True
        self.update()

    def setPosition(self, pos: Union[Frame, timedelta]) -> None:
        if self.rectF.width() == 0:
            self.cursorFT = pos

        if   isinstance(pos, Frame):
            self.cursorX = self.fToX(pos)
        elif isinstance(pos, timedelta):
            self.cursorX = self.tToX(pos)
        else:
            raise TypeError(f'Timeline.setPosition(): pos of type {type(pos)} isn\'t supported.')
        self.update()

    def tToX(self, t: timedelta) -> int:
        width = self.rectF.width()
        x     = round(t.total_seconds() / self.totalT.total_seconds() * width)
        return x

    def xToT(self, x: int) -> timedelta:
        width = self.rectF.width()
        return timedelta(seconds=(x * self.totalT.total_seconds() / width))

    def fToX(self, f: Frame) -> int:
        t = self.main.to_timedelta(f)
        x = self.tToX(t)
        return x

    def xToF(self, x: int) -> Frame:
        t = self.xToT(x)
        return self.main.to_frame(t)
