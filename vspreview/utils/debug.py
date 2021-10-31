from __future__ import annotations

from   functools import wraps
import inspect
import logging
import re
from   time      import perf_counter_ns
from   typing    import Any, Callable, cast, Dict, Type, TypeVar, Tuple, Union

from   pprint      import pprint
from   PyQt5       import Qt, sip
import vapoursynth as     vs

from vspreview.core import AbstractMainWindow


T = TypeVar('T')


def print_var(var: Any) -> None:
    current_frame = inspect.currentframe()
    if current_frame is None:
        logging.debug('print_var(): current_frame is None')
        return

    frame = current_frame.f_back
    if current_frame.f_back is None:
        logging.debug('print_var(): f_back is None')

    context = inspect.getframeinfo(frame).code_context
    if context is None:
        logging.debug('print_var(): code_context is None')
        return
    s = context[0]

    match = re.search(r"\((.*)\)", s)
    if match is None:
        logging.debug('print_var(): match is None')
        return
    r = match.group(1)
    logging.debug(f'{r}: {var}')


def print_func_name() -> None:
    logging.debug(f'{inspect.stack()[1][3]}()')


class EventFilter(Qt.QObject):
    __slots__ = (
        'main',
    )

    def __init__(self, main: AbstractMainWindow) -> None:
        super().__init__()
        self.main = main

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

    def run_get_frame_test(self) -> None:
        N = 10

        start_frame_async = 1000
        total_async = 0
        for i in range(start_frame_async, start_frame_async + N):
            s1 = perf_counter_ns()
            f1 = self.main.current_output.vs_output.get_frame_async(i)
            f1.result()
            s2 = perf_counter_ns()
            logging.debug(f'async test time: {s2 - s1} ns')
            if i != start_frame_async:
                total_async += s2 - s1
        logging.debug('')

        start_frame_sync = 2000
        total_sync = 0
        for i in range(start_frame_sync, start_frame_sync + N):
            s1 = perf_counter_ns()
            f2 = self.main.current_output.vs_output.get_frame(i)  # pylint: disable=unused-variable
            s2 = perf_counter_ns()
            logging.debug(f'sync test time: {s2 - s1} ns')
            if i != start_frame_sync:
                total_sync += s2 - s1

        logging.debug('')
        logging.debug(
            f'Async average: {total_async / N - 1} ns, {1_000_000_000 / (total_async / N - 1)} fps')
        logging.debug(
            f'Sync average:  {total_sync  / N - 1} ns, {1_000_000_000 / (total_sync  / N - 1)} fps')


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


def profile_cpu(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def decorator(*args: Any, **kwargs: Any) -> T:
        from cProfile import Profile
        from pstats   import Stats, SortKey

        p = Profile(perf_counter_ns, 0.000_000_001, True, False)
        ret = p.runcall(func, *args, **kwargs)

        s = Stats(p)
        s.sort_stats(SortKey.TIME)
        s.print_stats(10)
        return ret
    return decorator


def print_vs_output_colorspace_info(vs_output: vs.VideoNode) -> None:
    from vspreview.core import Output

    props = vs_output.get_frame(0).props
    logging.debug('Matrix: {}, Transfer: {}, Primaries: {}, Range: {}'.format(
        Output.Matrix   .values[props['_Matrix']]     if '_Matrix'     in props else None,
        Output.Transfer .values[props['_Transfer']]   if '_Transfer'   in props else None,
        Output.Primaries.values[props['_Primaries']]  if '_Primaries'  in props else None,
        Output.Range    .values[props['_ColorRange']] if '_ColorRange' in props else None,
    ))


class DebugMeta(sip.wrappertype):
    def __new__(cls: Type[type], name: str, bases: Tuple[type, ...], dct: Dict[str, Any]) -> DebugMeta:
        from functools import partialmethod

        base = bases[0]
        for attr in dir(base):
            if not attr.endswith('__') and callable(getattr(base, attr)):
                dct[attr] = partialmethod(DebugMeta.dummy_method, attr)
        subcls = super(DebugMeta, cls).__new__(cls, name, bases, dct)  # type: ignore
        return cast(DebugMeta, subcls)

    def dummy_method(self, name: str, *args: Any, **kwargs: Any) -> Any:
        method = getattr(super(GraphicsScene, GraphicsScene), name)
        method = measure_exec_time_ms(method)
        return method(self, *args, **kwargs)


class GraphicsScene(Qt.QGraphicsScene, metaclass=DebugMeta):  # type: ignore
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


qevent_info = {
    0: ('None', 'invalid event'),
    1: ('Timer', 'timer event'),
    2: ('MouseButtonPress', 'mouse button pressed'),
    3: ('MouseButtonRelease', 'mouse button released'),
    4: ('MouseButtonDblClick', 'mouse button double click'),
    5: ('MouseMove', 'mouse move'),
    6: ('KeyPress', 'key pressed'),
    7: ('KeyRelease', 'key released'),
    8: ('FocusIn', 'keyboard focus received'),
    9: ('FocusOut', 'keyboard focus lost'),
    23: ('FocusAboutToChange', 'keyboard focus is about to be lost'),
    10: ('Enter', 'mouse enters widget'),
    11: ('Leave', 'mouse leaves widget'),
    12: ('Paint', 'paint widget'),
    13: ('Move', 'move widget'),
    14: ('Resize', 'resize widget'),
    15: ('Create', 'after widget creation'),
    16: ('Destroy', 'during widget destruction'),
    17: ('Show', 'widget is shown'),
    18: ('Hide', 'widget is hidden'),
    19: ('Close', 'request to close widget'),
    20: ('Quit', 'request to quit application'),
    21: ('ParentChange', 'widget has been reparented'),
    131: ('ParentAboutToChange', 'sent just before the parent change is done'),
    22: ('ThreadChange', 'object has changed threads'),
    24: ('WindowActivate', 'window was activated'),
    25: ('WindowDeactivate', 'window was deactivated'),
    26: ('ShowToParent', 'widget is shown to parent'),
    27: ('HideToParent', 'widget is hidden to parent'),
    31: ('Wheel', 'wheel event'),
    33: ('WindowTitleChange', 'window title changed'),
    34: ('WindowIconChange', 'icon changed'),
    35: ('ApplicationWindowIconChange', 'application icon changed'),
    36: ('ApplicationFontChange', 'application font changed'),
    37: ('ApplicationLayoutDirectionChange', 'application layout direction changed'),
    38: ('ApplicationPaletteChange', 'application palette changed'),
    39: ('PaletteChange', 'widget palette changed'),
    40: ('Clipboard', 'internal clipboard event'),
    42: ('Speech', 'reserved for speech input'),
    43: ('MetaCall', 'meta call event'),
    50: ('SockAct', 'socket activation'),
    132: ('WinEventAct', 'win event activation'),
    52: ('DeferredDelete', 'deferred delete event'),
    60: ('DragEnter', 'drag moves into widget'),
    61: ('DragMove', 'drag moves in widget'),
    62: ('DragLeave', 'drag leaves or is cancelled'),
    63: ('Drop', 'actual drop'),
    64: ('DragResponse', 'drag accepted/rejected'),
    68: ('ChildAdded', 'new child widget'),
    69: ('ChildPolished', 'polished child widget'),
    71: ('ChildRemoved', 'deleted child widget'),
    73: ('ShowWindowRequest', 'widget\'s window should be mapped'),
    74: ('PolishRequest', 'widget should be polished'),
    75: ('Polish', 'widget is polished'),
    76: ('LayoutRequest', 'widget should be relayouted'),
    77: ('UpdateRequest', 'widget should be repainted'),
    78: ('UpdateLater', 'request update() later'),

    79: ('EmbeddingControl', 'ActiveX embedding'),
    80: ('ActivateControl', 'ActiveX activation'),
    81: ('DeactivateControl', 'ActiveX deactivation'),
    82: ('ContextMenu', 'context popup menu'),
    83: ('InputMethod', 'input method'),
    87: ('TabletMove', 'Wacom tablet event'),
    88: ('LocaleChange', 'the system locale changed'),
    89: ('LanguageChange', 'the application language changed'),
    90: ('LayoutDirectionChange', 'the layout direction changed'),
    91: ('Style', 'internal style event'),
    92: ('TabletPress', 'tablet press'),
    93: ('TabletRelease', 'tablet release'),
    94: ('OkRequest', 'CE (Ok) button pressed'),
    95: ('HelpRequest', 'CE (?)  button pressed'),

    96: ('IconDrag', 'proxy icon dragged'),

    97: ('FontChange', 'font has changed'),
    98: ('EnabledChange', 'enabled state has changed'),
    99: ('ActivationChange', 'window activation has changed'),
    100: ('StyleChange', 'style has changed'),
    101: ('IconTextChange', 'icon text has changed.  Deprecated.'),
    102: ('ModifiedChange', 'modified state has changed'),
    109: ('MouseTrackingChange', 'mouse tracking state has changed'),

    103: ('WindowBlocked', 'window is about to be blocked modally'),
    104: ('WindowUnblocked', 'windows modal blocking has ended'),
    105: ('WindowStateChange', ''),

    106: ('ReadOnlyChange', 'readonly state has changed'),

    110: ('ToolTip', ''),
    111: ('WhatsThis', ''),
    112: ('StatusTip', ''),

    113: ('ActionChanged', ''),
    114: ('ActionAdded', ''),
    115: ('ActionRemoved', ''),

    116: ('FileOpen', 'file open request'),

    117: ('Shortcut', 'shortcut triggered'),
    51: ('ShortcutOverride', 'shortcut override request'),

    118: ('WhatsThisClicked', ''),

    120: ('ToolBarChange', 'toolbar visibility toggled'),

    121: ('ApplicationActivate',
          'deprecated. Use ApplicationStateChange instead.'),
    122: ('ApplicationDeactivate',
          'deprecated. Use ApplicationStateChange instead.'),

    123: ('QueryWhatsThis', 'query what\'s this widget help'),
    124: ('EnterWhatsThisMode', ''),
    125: ('LeaveWhatsThisMode', ''),

    126: ('ZOrderChange', 'child widget has had its z-order changed'),

    127: ('HoverEnter', 'mouse cursor enters a hover widget'),
    128: ('HoverLeave', 'mouse cursor leaves a hover widget'),
    129: ('HoverMove', 'mouse cursor move inside a hover widget'),

    150: ('EnterEditFocus', 'enter edit mode in keypad navigation'),
    151: ('LeaveEditFocus', 'enter edit mode in keypad navigation'),
    152: ('AcceptDropsChange', ''),

    154: ('ZeroTimerEvent', 'Used for Windows Zero timer events'),

    155: ('GraphicsSceneMouseMove', 'GraphicsView'),
    156: ('GraphicsSceneMousePress', ''),
    157: ('GraphicsSceneMouseRelease', ''),
    158: ('GraphicsSceneMouseDoubleClick', ''),
    159: ('GraphicsSceneContextMenu', ''),
    160: ('GraphicsSceneHoverEnter', ''),
    161: ('GraphicsSceneHoverMove', ''),
    162: ('GraphicsSceneHoverLeave', ''),
    163: ('GraphicsSceneHelp', ''),
    164: ('GraphicsSceneDragEnter', ''),
    165: ('GraphicsSceneDragMove', ''),
    166: ('GraphicsSceneDragLeave', ''),
    167: ('GraphicsSceneDrop', ''),
    168: ('GraphicsSceneWheel', ''),

    169: ('KeyboardLayoutChange', 'keyboard layout changed'),

    170: ('DynamicPropertyChange',
          'A dynamic property was changed through setProperty/property'),

    171: ('TabletEnterProximity', ''),
    172: ('TabletLeaveProximity', ''),

    173: ('NonClientAreaMouseMove', ''),
    174: ('NonClientAreaMouseButtonPress', ''),
    175: ('NonClientAreaMouseButtonRelease', ''),
    176: ('NonClientAreaMouseButtonDblClick', ''),

    177: ('MacSizeChange',
          'when the Qt::WA_Mac{Normal,Small,Mini}Size changes'),

    178: ('ContentsRectChange',
          'sent by QWidget::setContentsMargins (internal)'),

    179: ('MacGLWindowChange',
          'Internal! the window of the GLWidget has changed'),

    180: ('FutureCallOut', ''),

    181: ('GraphicsSceneResize', ''),
    182: ('GraphicsSceneMove', ''),

    183: ('CursorChange', ''),
    184: ('ToolTipChange', ''),

    185: ('NetworkReplyUpdated', 'Internal for QNetworkReply'),

    186: ('GrabMouse', ''),
    187: ('UngrabMouse', ''),
    188: ('GrabKeyboard', ''),
    189: ('UngrabKeyboard', ''),
    191: ('MacGLClearDrawable',
          'Internal Cocoa, the window has changed, so we must clear'),

    192: ('StateMachineSignal', ''),
    193: ('StateMachineWrapped', ''),

    194: ('TouchBegin', ''),
    195: ('TouchUpdate', ''),
    196: ('TouchEnd', ''),

    197: ('NativeGesture', 'QtGui native gesture'),
    199: ('RequestSoftwareInputPanel', ''),
    200: ('CloseSoftwareInputPanel', ''),

    203: ('WinIdChange', ''),
    198: ('Gesture', ''),
    202: ('GestureOverride', ''),
    204: ('ScrollPrepare', ''),
    205: ('Scroll', ''),

    206: ('Expose', ''),

    207: ('InputMethodQuery', ''),
    208: ('OrientationChange', 'Screen orientation has changed'),

    209: ('TouchCancel', ''),

    210: ('ThemeChange', ''),

    211: ('SockClose', 'socket closed'),

    212: ('PlatformPanel', ''),

    213: ('StyleAnimationUpdate', 'style animation target should be updated'),
    214: ('ApplicationStateChange', ''),

    215: ('WindowChangeInternal', 'internal for QQuickWidget'),
    216: ('ScreenChangeInternal', ''),

    217: ('PlatformSurface',
          'Platform surface created or about to be destroyed'),

    218: ('Pointer', 'QQuickPointerEvent; ### Qt 6: QPointerEvent'),

    219: ('TabletTrackingChange', 'tablet tracking state has changed'),

    512: ('reserved', 'reserved for Qt Jambi\'s MetaCall event'),
    513: ('reserved', 'reserved for Qt Jambi\'s DeleteOnMainThread event'),

    1000: ('User', 'first user event id'),
    65535: ('MaxUser', 'last user event id'),
}


class Application(Qt.QApplication):
    enter_count = 0

    def notify(self, obj: Qt.QObject, event: Qt.QEvent) -> bool:
        import sys

        isex = False
        try:
            self.enter_count += 1
            ret, time = cast(
                Tuple[bool, float],
                measure_exec_time_ms(
                    Qt.QApplication.notify, True, False)(self, obj, event))

            if (type(event).__name__ == 'QEvent'
                    and event.type() in qevent_info):
                event_name = qevent_info[event.type()][0]
            else:
                event_name = type(event).__name__

            try:
                obj_name = obj.objectName()
            except RuntimeError:
                obj_name = ''

            if obj_name == '':
                try:
                    if (obj.parent() is not None
                            and obj.parent().objectName() != ''):
                        obj_name = '(parent) ' + obj.parent().objectName()
                except RuntimeError:
                    pass

            recursive_indent = 2 * (self.enter_count - 1)

            print(
                f'{time:7.3f} ms, receiver: {type(obj).__name__:>25}, event: {event.type():3d} {" " * recursive_indent + event_name:<30}, name: {obj_name}')

            self.enter_count -= 1

            return ret
        except Exception:  # pylint: disable=broad-except
            isex = True
            logging.error('Application: unexpected error')
            print(*sys.exc_info())
            return False
        finally:
            if isex:
                self.quit()
