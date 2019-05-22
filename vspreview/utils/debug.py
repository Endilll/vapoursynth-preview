from __future__ import annotations

from   functools import wraps
import inspect
import logging
import re
from   time      import perf_counter_ns, time
from   typing    import Any, Callable, cast, Dict, Type, TypeVar, Tuple, Union

from pprint import pprint
from PyQt5  import Qt, sip

from vspreview.core import AbstractMainWindow


T = TypeVar('T')


def print_var(var: Any) -> None:
    frame = inspect.currentframe().f_back  # type: ignore
    s = inspect.getframeinfo(frame).code_context[0]
    r = re.search(r"\((.*)\)", s).group(1)  # type: ignore
    logging.debug(f'{r}: {var}')


def print_func_name() -> None:
    logging.debug(f'{inspect.stack()[1][3]}()')


class EventFilter(Qt.QObject):
    __slots__ = (
        'main',
    )

    def __init__(self, main_window: AbstractMainWindow) -> None:
        super().__init__()
        self.main = main_window

    def eventFilter(self, obj: Qt.QObject, event: Qt.QEvent) -> bool:
        if   (event.type() == Qt.QEvent.Show):
            logging.debug( '--------------------------------')
            logging.debug(f'{obj.objectName()}')
            logging.debug( 'event:       Show')
            logging.debug(f'spontaneous: {event.spontaneous()}')
            logging.debug( '')
            self.print_toolbars_state()
        elif (event.type() == Qt.QEvent.Hide):
            logging.debug( '--------------------------------')
            logging.debug(f'[{time()}]')
            logging.debug(f'{obj.objectName()}')
            logging.debug( 'event:       Hide')
            logging.debug(f'spontaneous: {event.spontaneous()}')
            logging.debug( '')
            self.print_toolbars_state()

        # return Qt.QObject.eventFilter(object, event)
        return False

    def print_toolbars_state(self) -> None:
        logging.debug(f'main toolbar:     {self.main.main_toolbar_widget.isVisible()}')
        logging.debug(f'playback toolbar: {self.main.toolbars.playback  .isVisible()}')
        logging.debug(f'scening toolbar:  {self.main.toolbars.scening   .isVisible()}')
        logging.debug(f'misc toolbar:     {self.main.toolbars.misc      .isVisible()}')

    def run_get_frame_test(self, main_window: AbstractMainWindow) -> None:
        N = 10

        start_frame_async = 1000
        total_async = 0
        for i in range(start_frame_async, start_frame_async + N):
            s1 = perf_counter_ns()
            f1 = main_window.current_output.vs_output.get_frame_async(i)
            f1.result()
            s2 = perf_counter_ns()
            logging.debug(f'async test time: {s2 - s1} ns')
            if i != start_frame_async:
                total_async += s2 - s1
        # logging.debug('')

        start_frame_sync = 2000
        total_sync = 0
        for i in range(start_frame_sync, start_frame_sync + N):
            s1 = perf_counter_ns()
            f2 = main_window.current_output.vs_output.get_frame(i)  # pylint: disable=unused-variable
            s2 = perf_counter_ns()
            # logging.debug(f'sync test time: {s2 - s1} ns')
            if i != start_frame_sync:
                total_sync += s2 - s1

        logging.debug('')
        logging.debug(f'Async average: {total_async / N - 1} ns, {1_000_000_000 / (total_async / N - 1)} fps')
        logging.debug(f'Sync average:  {total_sync  / N - 1} ns, {1_000_000_000 / (total_sync  / N - 1)} fps')


def measure_exec_time_ms(func: Callable[..., T], return_exec_time: bool = False, print_exec_time: bool = True) -> Callable[..., Union[T, Tuple[T, float]]]:
    @wraps(func)
    def decorator(*args: Any, **kwargs: Any) -> T:
        t1 = perf_counter_ns()
        ret = func(*args, **kwargs)
        t2 = perf_counter_ns()
        exec_time = (t2 - t1) / 1_000_000
        if print_exec_time:
            logging.debug(f'{exec_time:7.3f} ms: {func.__name__}()')
        if return_exec_time:
            return ret, exec_time  # type: ignore
        return ret
    return decorator


def print_perf_timepoints(*args: int) -> None:
    if len(args) < 2:
        raise ValueError('At least 2 timepoints required')
    for i in range(1, len(args)):
        logging.debug(f'{i}: {args[i] - args[i-1]} ns')


class DebugMeta(sip.wrappertype):  # type: ignore
    def __new__(cls: Type[type], name: str, bases: Tuple[type, ...], dct: Dict[str, Any]) -> type:
        from functools import partialmethod

        base = bases[0]
        # attr_list = ['activePanel', 'activeWindow', 'addEllipse', 'addItem', 'addLine', 'addPath', 'addPixmap', 'addPolygon', 'addRect', 'addSimpleText', 'addText', 'addWidget', 'backgroundBrush', 'bspTreeDepth', 'clearFocus', 'collidingItems', 'createItemGroup', 'destroyItemGroup', 'focusItem', 'font', 'foregroundBrush', 'hasFocus', 'height', 'inputMethodQuery', 'invalidate', 'isActive', 'itemAt', 'itemIndexMethod', 'items', 'itemsBoundingRect', 'minimumRenderSize', 'mouseGrabberItem', 'palette', 'removeItem', 'render', 'sceneRect', 'selectedItems', 'selectionArea', 'sendEvent', 'setActivePanel', 'setActiveWindow','setBackgroundBrush', 'setBspTreeDepth', 'setFocus', 'setFocusItem', 'setFont', 'setForegroundBrush', 'setItemIndexMethod', 'setMinimumRenderSize', 'setPalette', 'setSceneRect', 'setSelectionArea', 'setStickyFocus', 'setStyle', 'stickyFocus', 'style', 'update', 'views', 'width']
        for attr in dir(base):
            if not attr.endswith('__') and callable(getattr(base, attr)):
                dct[attr] = partialmethod(DebugMeta.dummy_method, attr)
        subcls = super(DebugMeta, cls).__new__(cls, name, bases, dct)
        return cast(type, subcls)

    def dummy_method(self, name: str, *args: Any, **kwargs: Any) -> Any:
        method = getattr(super(GraphicsScene, GraphicsScene), name)
        method = measure_exec_time_ms(method)
        return method(self, *args, **kwargs)


class GraphicsScene(Qt.QGraphicsScene, metaclass=DebugMeta):  # pylint: disable=invalid-metaclass
    def event(self, event: Qt.QEvent) -> bool:
        t0 = perf_counter_ns()
        ret = super().event(event)
        t1 = perf_counter_ns()
        interval = t1 - t0
        if interval > 5_000_000:
            print(self.__class__.__name__ + '.event()')
            print(f'{interval / 1_000_000}: {event.type()}')

        return ret

    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if callable(attr):
            return measure_exec_time_ms(attr)
