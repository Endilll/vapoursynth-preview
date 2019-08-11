from __future__ import annotations

from   functools import wraps
import logging
from   time      import perf_counter_ns
from   typing    import Any, Callable, cast, Tuple, TypeVar, Union

from PySide2.QtCore    import QEvent, QObject
from PySide2.QtWidgets import QApplication

T = TypeVar('T')


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


class Application(QApplication):
    enter_count = 0

    def notify(self, obj: QObject, event: QEvent) -> bool:
        isex = False
        try:
            self.enter_count += 1
            ret, time = cast(
                Tuple[bool, float],
                measure_exec_time_ms(QApplication.notify, True, False)(self, obj, event)
            )
            self.enter_count -= 1

            event_name = str(event.type()).rsplit(".", 1)[1]

            try:
                obj_name = obj.objectName()
            except RuntimeError:
                obj_name = ''

            if obj_name == '':
                try:
                    if obj.parent() is not None and obj.parent().objectName() != '':
                        obj_name = '(parent) ' + obj.parent().objectName()
                except RuntimeError:
                    pass

            recursive_indent = 2 * (self.enter_count - 1)

            print(f'{time:7.3f} ms, receiver: {type(obj).__name__:>25}, event: {" " * recursive_indent + event_name:<32}, name: {obj_name}')

            return ret
        except Exception as e:  # pylint: disable=broad-except
            isex = True
            logging.error('Application: unexpected error')
            print(e)
            return False
        finally:
            if isex:
                self.quit()  # type: ignore
