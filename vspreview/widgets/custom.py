from __future__ import annotations

# import logging
from typing import Optional

from PyQt5 import Qt  # , sip

# import debug


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


# class DebugMeta(sip.wrappertype):
#     def __new__(cls, name, bases, dct) -> type:
#         from functools import partialmethod

#         base = bases[0]
#         # attr_list = ['activePanel', 'activeWindow', 'addEllipse', 'addItem', 'addLine', 'addPath', 'addPixmap', 'addPolygon', 'addRect', 'addSimpleText', 'addText', 'addWidget', 'backgroundBrush', 'bspTreeDepth', 'clearFocus', 'collidingItems', 'createItemGroup', 'destroyItemGroup', 'focusItem', 'font', 'foregroundBrush', 'hasFocus', 'height', 'inputMethodQuery', 'invalidate', 'isActive', 'itemAt', 'itemIndexMethod', 'items', 'itemsBoundingRect', 'minimumRenderSize', 'mouseGrabberItem', 'palette', 'removeItem', 'render', 'sceneRect', 'selectedItems', 'selectionArea', 'sendEvent', 'setActivePanel', 'setActiveWindow','setBackgroundBrush', 'setBspTreeDepth', 'setFocus', 'setFocusItem', 'setFont', 'setForegroundBrush', 'setItemIndexMethod', 'setMinimumRenderSize', 'setPalette', 'setSceneRect', 'setSelectionArea', 'setStickyFocus', 'setStyle', 'stickyFocus', 'style', 'update', 'views', 'width']
#         for attr in dir(base):
#             if not attr.endswith('__') and callable(getattr(base, attr)):
#                 dct[attr] = partialmethod(DebugMeta.dummy_method, attr)
#         subcls = super(DebugMeta, cls).__new__(cls, name, bases, dct)
#         return subcls

#     def dummy_method(self, name, *args, **kwargs):
#         from debug import measure_exec_time
#         method = getattr(super(GraphicsScene, GraphicsScene), name)
#         method = measure_exec_time(method)
#         return method(self, *args, **kwargs)


# class GraphicsScene(Qt.QGraphicsScene, metaclass=DebugMeta):  # pylint: disable=invalid-metaclass
#     pass
    # def event(self, event: Qt.QEvent) -> bool:
    #     from time import perf_counter_ns

    #     t0 = perf_counter_ns()
    #     ret = super().event(event)
    #     t1 = perf_counter_ns()
    #     interval = t1 - t0
    #     if interval > 5000000:
    #         print(self.__class__.__name__ + '.event()')
    #         print(f'{interval / 1000000}: {event.type()}')

    #     return ret

    # def __getattribute__(self, name):
    #     from debug import measure_exec_time
    #     attr = super().__getattribute__(name)
    #     if callable(attr):
    #         return measure_exec_time(attr)
