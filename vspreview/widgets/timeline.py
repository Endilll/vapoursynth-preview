from __future__ import annotations

from   datetime import timedelta
from   enum import auto, Enum
import logging
from   typing   import Any, cast, Dict, Iterator, List, Optional, Tuple, Union

from PyQt5 import Qt
from yaml  import YAMLObject

from vspreview.core  import AbstractToolbar, Frame, FrameInterval, Scene
from vspreview.utils import debug

# pylint: disable=attribute-defined-outside-init

# TODO: store cursor pos as frame
# TODO: consider moving from ints to floats
# TODO: make Timeline.Mode a proper class instead of bunch of strings


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

    class Mode(YAMLObject):
        FRAME = 'frame'
        TIME  = 'time'

        yaml_tag = '!Timeline.Mode'

        @classmethod
        def is_valid(cls, value: str) -> bool:
            return value in (
                cls.FRAME,
                cls.TIME
            )

    clicked = Qt.pyqtSignal(Frame, timedelta)

    def __init__(self, parent: Qt.QWidget) -> None:
        from vspreview.utils import main_window

        super().__init__(parent)
        self.app  = Qt.QApplication.instance()
        self.main = main_window()

        self._mode = self.Mode.TIME

        self.rect_f  = Qt.QRectF()

        self.total_t = timedelta(seconds=1)
        self.total_f = Frame(1)

        self.notch_interval_target_x = round(75 * self.main.display_scale)
        self.notch_height            = round( 6 * self.main.display_scale)
        self.font_height             = round(10 * self.main.display_scale)
        self.notch_label_interval    = round(-1 * self.main.display_scale)
        self.notch_scroll_interval   = round( 2 * self.main.display_scale)
        self.scroll_height           = round(10 * self.main.display_scale)

        self.setMinimumSize(self.notch_interval_target_x, round(33 * self.main.display_scale))

        font = self.font()
        font.setPixelSize(self.font_height)
        self.setFont(font)

        self.cursor_x = 0
        # used as a fallback when self.rectF.width() is 0, so cursorX is incorrect
        self.cursor_ft: Optional[Union[Frame, timedelta]] = None
        # False means that only cursor position'll be recalculated
        self.need_full_repaint = True

        self.toolbars_notches: Dict[AbstractToolbar, Notches] = {}

        self.setAttribute(Qt.Qt.WA_OpaquePaintEvent)
        self.setMouseTracking(True)

    def paintEvent(self, event: Qt.QPaintEvent) -> None:
        super().paintEvent(event)
        self.rect_f = Qt.QRectF(event.rect())
        # self.rectF.adjust(0, 0, -1, -1)

        if self.cursor_ft is not None:
            self.set_position(self.cursor_ft)
        self.cursor_ft = None

        painter = Qt.QPainter(self)
        self.drawWidget(painter)

    def drawWidget(self, painter: Qt.QPainter) -> None:
        from copy import deepcopy

        from vspreview.utils import strfdelta

        # calculations

        if self.need_full_repaint:
            labels_notches = Notches()
            label_notch_bottom = self.rect_f.top() + self.font_height + self.notch_label_interval + self.notch_height + 5
            label_notch_top    = label_notch_bottom - self.notch_height
            label_notch_x = self.rect_f.left()

            if self.mode == self.Mode.TIME:
                notch_interval_t = self.calculate_notch_interval_t(self.notch_interval_target_x)
                label_format = self.generate_label_format(notch_interval_t)
                label_notch_t = timedelta(0)

                while (label_notch_x < self.rect_f.right() and label_notch_t < self.total_t):
                    line = Qt.QLineF(label_notch_x, label_notch_bottom, label_notch_x, label_notch_top)
                    labels_notches.add(Notch(label_notch_t, line=line))
                    label_notch_t += notch_interval_t
                    label_notch_x  = self.t_to_x(label_notch_t)

            elif self.mode == self.Mode.FRAME:
                notch_interval_f = self.calculate_notch_interval_f(self.notch_interval_target_x)
                label_notch_f = Frame(0)

                while (label_notch_x < self.rect_f.right() and label_notch_f < self.total_f):
                    line = Qt.QLineF(label_notch_x, label_notch_bottom, label_notch_x, label_notch_top)
                    labels_notches.add(Notch(deepcopy(label_notch_f), line=line))
                    label_notch_f += notch_interval_f
                    label_notch_x  = self.f_to_x(label_notch_f)

            self.scroll_rect = Qt.QRectF(self.rect_f.left(), label_notch_bottom + self.notch_scroll_interval, self.rect_f.width(), self.scroll_height)

            for toolbar, notches in self.toolbars_notches.items():
                if not toolbar.is_notches_visible():
                    continue

                for notch in notches:
                    if   isinstance(notch.data, Frame):
                        x = self.f_to_x(notch.data)
                    elif isinstance(notch.data, timedelta):
                        x = self.t_to_x(notch.data)
                    y = self.scroll_rect.top()
                    notch.line = Qt.QLineF(x, y, x, y + self.scroll_rect.height() - 1)

        cursor_line = Qt.QLineF(self.cursor_x, self.scroll_rect.top(), self.cursor_x, self.scroll_rect.top() + self.scroll_rect.height() - 1)

        # drawing

        if self.need_full_repaint:
            painter.fillRect(self.rect_f, self.palette().color(Qt.QPalette.Window))

            painter.setPen(Qt.QPen(self.palette().color(Qt.QPalette.WindowText)))
            painter.setRenderHint(Qt.QPainter.Antialiasing, False)
            painter.drawLines([notch.line for notch in labels_notches])

            painter.setRenderHint(Qt.QPainter.Antialiasing)
            for i, notch in enumerate(labels_notches):
                line = notch.line
                anchor_rect = Qt.QRectF(line.x2(), line.y2() - self.notch_label_interval, 0, 0)

                if self.mode == self.Mode.TIME:
                    t     = cast(timedelta, notch.data)
                    label = strfdelta(t, label_format)
                if self.mode == self.Mode.FRAME:
                    label = str(notch.data)

                if   i == 0:
                    rect = painter.boundingRect(anchor_rect, Qt.Qt.AlignBottom + Qt.Qt.AlignLeft, label)
                    if self.mode == self.Mode.TIME:
                        rect.moveLeft(-2.5)
                elif i == (len(labels_notches) - 1):
                    rect = painter.boundingRect(anchor_rect, Qt.Qt.AlignBottom + Qt.Qt.AlignHCenter, label)
                    if rect.right() > self.rect_f.right():
                        rect = painter.boundingRect(anchor_rect, Qt.Qt.AlignBottom + Qt.Qt.AlignRight, label)
                else:
                    rect = painter.boundingRect(anchor_rect, Qt.Qt.AlignBottom + Qt.Qt.AlignHCenter, label)
                painter.drawText(rect, label)

        painter.setRenderHint(Qt.QPainter.Antialiasing, False)
        painter.fillRect(self.scroll_rect, Qt.Qt.gray)

        for toolbar, notches in self.toolbars_notches.items():
            if not toolbar.is_notches_visible():
                continue

            for notch in notches:
                painter.setPen(notch.color)
                painter.drawLine(notch.line)

        painter.setPen(Qt.Qt.black)
        painter.drawLine(cursor_line)

        self.need_full_repaint = False

    def moveEvent(self, event: Qt.QMoveEvent) -> None:
        super().moveEvent(event)
        self.update()

    def mousePressEvent(self, event: Qt.QMouseEvent) -> None:
        super().mousePressEvent(event)
        pos = Qt.QPoint(event.pos())
        if self.scroll_rect.contains(pos):
            self.cursor_x = pos.x()
            self.clicked.emit(self.x_to_f(self.cursor_x), self.x_to_t(self.cursor_x))
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
        if event.type() in (Qt.QEvent.Polish, Qt.QEvent.ApplicationPaletteChange):
            self.setPalette(self.main.palette())
            self.update()
            return True

        return super().event(event)

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.need_full_repaint = True
        super().update(*args, **kwargs)

    def update_notches(self, toolbar: Optional[AbstractToolbar] = None) -> None:
        if toolbar is not None:
            self.toolbars_notches[toolbar] = toolbar.get_notches()
        if toolbar is None:
            for t in self.main.toolbars:
                self.toolbars_notches[t] = t.get_notches()
        self.update()

    @property
    def mode(self) -> str:  # pylint: disable=undefined-variable
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        if value == self._mode:
            return

        self._mode = value
        self.update()


    def calculate_notch_interval_t(self, target_interval_x: int) -> timedelta:
        intervals = (
            timedelta(seconds=  1),
            timedelta(seconds=  2),
            timedelta(seconds=  5),
            timedelta(seconds= 10),
            timedelta(seconds= 15),
            timedelta(seconds= 30),
            timedelta(seconds= 60),
            timedelta(seconds= 90),
            timedelta(seconds=120),
            timedelta(seconds=300)
        )
        margin  = 1 + self.main.TIMELINE_LABEL_NOTCHES_MARGIN / 100
        target_interval_t = self.x_to_t(target_interval_x)
        for interval in intervals:
            if target_interval_t < interval * margin:
                return interval
        return intervals[-1]

    def calculate_notch_interval_f(self, target_interval_x: int) -> FrameInterval:
        intervals = (
            FrameInterval(    1),
            FrameInterval(    5),
            FrameInterval(   10),
            FrameInterval(   20),
            FrameInterval(   25),
            FrameInterval(   50),
            FrameInterval(   75),
            FrameInterval(  100),
            FrameInterval(  200),
            FrameInterval(  250),
            FrameInterval(  500),
            FrameInterval(  750),
            FrameInterval( 1000),
            FrameInterval( 2000),
            FrameInterval( 2500),
            FrameInterval( 5000),
            FrameInterval( 7500),
            FrameInterval(10000),
        )
        margin  = 1 + self.main.TIMELINE_LABEL_NOTCHES_MARGIN / 100
        target_interval_f = self.x_to_f(target_interval_x)
        for interval in intervals:
            if target_interval_f < interval * margin:
                return interval
        return intervals[-1]

    def generate_label_format(self, notch_interval_t: timedelta) -> str:
        if   notch_interval_t >= timedelta(hours=1):
            return '%h:%M'
        elif notch_interval_t >= timedelta(minutes=1):
            return '%m:00'
        else:
            return '%m:%S'

    def set_duration(self, total_f: Frame, total_t: timedelta) -> None:
        self.total_f = total_f
        self.total_t = total_t
        self.need_full_repaint = True
        self.update()

    def set_position(self, pos: Union[Frame, timedelta]) -> None:
        if self.rect_f.width() == 0:
            self.cursor_ft = pos

        if   isinstance(pos, Frame):
            self.cursor_x = self.f_to_x(pos)
        elif isinstance(pos, timedelta):
            self.cursor_x = self.t_to_x(pos)
        else:
            raise TypeError(f'Timeline.set_position(): pos of type {type(pos)} isn\'t supported.')
        self.update()

    def t_to_x(self, t: timedelta) -> int:
        width = self.rect_f.width()
        x     = round(t.total_seconds() / self.total_t.total_seconds() * width)
        return x

    def x_to_t(self, x: int) -> timedelta:
        width = self.rect_f.width()
        return timedelta(seconds=(x * self.total_t.total_seconds() / width))

    def f_to_x(self, f: Frame) -> int:
        t = self.main.to_timedelta(f)
        x = self.t_to_x(t)
        return x

    def x_to_f(self, x: int) -> Frame:
        t = self.x_to_t(x)
        return self.main.to_frame(t)
