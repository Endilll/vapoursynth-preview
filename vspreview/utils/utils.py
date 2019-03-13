from __future__ import annotations

from   datetime  import timedelta
from   functools import partial, wraps
import logging
from   string    import Template
from   typing    import Any, Callable, MutableMapping, Optional, TYPE_CHECKING, TypeVar

from PyQt5 import Qt

from vspreview.utils import debug


T = TypeVar('T')


def timedelta_to_qtime(t: timedelta) -> Qt.QTime:
    return Qt.QTime(t.seconds // 3600,
                    t.seconds // 60,
                    t.seconds  % 60,
                    t.microseconds // 1000)


def qtime_to_timedelta(qtime: Qt.QTime) -> timedelta:
    return timedelta(milliseconds=qtime.msecsSinceStartOfDay())


# it is a BuiltinMethodType at the same time
def qt_silent_call(qt_method: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    # https://github.com/python/typing/issues/213
    qobject = qt_method.__self__  # type: ignore
    block = Qt.QSignalBlocker(qobject)
    ret = qt_method(*args, **kwargs)
    del(block)
    return ret


class DeltaTemplate(Template):
    delimiter = '%'


def strfdelta(t: timedelta, output_format: str) -> str:
    d: MutableMapping[str, str] = {}
    hours        = t.seconds      // 3600
    minutes      = t.seconds      //   60
    seconds      = t.seconds       %   60
    milliseconds = t.microseconds // 1000
    d['D'] =   '{:d}'.format(t.days)
    d['H'] = '{:02d}'.format(hours)
    d['M'] = '{:02d}'.format(minutes)
    d['S'] = '{:02d}'.format(seconds)
    d['Z'] = '{:03d}'.format(milliseconds)
    d['h'] =  '{:2d}'.format(hours)
    d['m'] =  '{:2d}'.format(minutes)
    d['s'] =  '{:2d}'.format(seconds)

    template = DeltaTemplate(output_format)
    return template.substitute(**d)


if TYPE_CHECKING:
    from vspreview.core import AbstractMainWindow


def main_window() -> AbstractMainWindow:
    from vspreview.core import AbstractMainWindow  # pylint: disable=redefined-outer-name

    app = Qt.QApplication.instance()
    if app is not None:
        for widget in app.topLevelWidgets():
            if isinstance(widget, AbstractMainWindow):
                return widget
    logging.critical('main_window() failed')
    app.exit()
    raise RuntimeError


def add_shortcut(key: int, handler: Callable[[], None], widget: Optional[Qt.QWidget] = None) -> None:
    if widget is None:
        widget = main_window()
    Qt.QShortcut(Qt.QKeySequence(key), widget).activated.connect(handler)


def fire_and_forget(f: Callable[..., T]) -> Callable[..., T]:
    from asyncio import get_event_loop

    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        loop = get_event_loop()
        if callable(f):
            return loop.run_in_executor(None, partial(f, *args, **kwargs))
        else:
            raise TypeError('fire_and_forget(): Task must be a callable')
    return wrapped


def set_status_label(label: str) -> Callable[..., T]:
    def decorator(func: Callable[..., T]) -> Any:
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> T:
            main = main_window()

            if main.statusbar.label.text() == 'Ready':
                # Qt.QMetaObject.invokeMethod(main.statusbar.label, 'setText', Qt.Qt.QueuedConnection,
                #                             Qt.Q_ARG(str, label))
                main.statusbar.label.setText(label)

            ret = func(*args, **kwargs)

            if main.statusbar.label.text() == label:
                # Qt.QMetaObject.invokeMethod(main.statusbar.label, 'setText', Qt.Qt.QueuedConnection,
                #                             Qt.Q_ARG(str, 'Ready'))
                main.statusbar.label.setText('Ready')

            return ret
        return wrapped
    return decorator


def method_dispatch(func: Callable[..., T]) -> Callable[..., T]:
    '''
    https://stackoverflow.com/a/24602374
    '''
    from functools import singledispatch, update_wrapper

    dispatcher = singledispatch(func)

    def wrapper(*args: Any, **kwargs: Any) -> T:
        return dispatcher.dispatch(args[1].__class__)(*args, **kwargs)

    wrapper.register = dispatcher.register  # type: ignore
    update_wrapper(wrapper, dispatcher)
    return wrapper
