from __future__ import annotations

from   functools import lru_cache
import logging
import sys
from   typing    import MutableMapping

from PySide2.QtWidgets import QApplication

from vspreview.core import TimeType, ViewModel


@lru_cache()
def main_view_model() -> ViewModel:
    from vspreview.main import MainView  # pylint: disable=redefined-outer-name

    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, MainView):
            return widget._data_context  # pylint: disable=protected-access

    logging.critical('MainView not found')
    raise RuntimeError


def strfdelta(time: TimeType, output_format: str) -> str:
    from string import Template

    class DeltaTemplate(Template):
        delimiter = '%'

    d: MutableMapping[str, str] = {}
    td = time.value
    hours        = td.seconds      // 3600
    minutes      = td.seconds      //   60
    seconds      = td.seconds       %   60
    milliseconds = td.microseconds // 1000
    d['D'] =   '{:d}'.format(td.days)
    d['H'] = '{:02d}'.format(hours)
    d['M'] = '{:02d}'.format(minutes)
    d['S'] = '{:02d}'.format(seconds)
    d['Z'] = '{:03d}'.format(milliseconds)
    d['h'] =   '{:d}'.format(hours)
    d['m'] =  '{:2d}'.format(minutes)
    d['s'] =  '{:2d}'.format(seconds)

    template = DeltaTemplate(output_format)
    return template.substitute(**d)


class Application(QApplication):
    from PySide2.QtCore import QEvent, QObject

    def notify(self, obj: QObject, event: QEvent) -> bool:
        isex = False
        try:
            return QApplication.notify(self, obj, event)
        except Exception:  # pylint: disable=broad-except
            isex = True
            logging.error('Application: unexpected error')
            print(*sys.exc_info())
            return False
        finally:
            if isex:
                self.quit()  # type: ignore


def check_dependencies() -> bool:
    from pkg_resources import get_distribution
    from platform import python_version
    from vapoursynth import core as vs_core

    if sys.version_info < (3, 7, 0, 'final', 0):
        print('VSPreview is not tested on Python versions prior to 3.7, but you have {}. Use at your own risk.'.format(
            python_version()))
        return False

    if get_distribution('PySide2').version < '5.13':
        print('VSPreview is not tested on PySide2 versions prior to 5.13, but you have {}. Use at your own risk.'.format(get_distribution('PySide2').version))
        return False

    if vs_core.version_number() < 47:
        print('VSPreview is not tested on VapourSynth versions prior to 47, but you have {}. Use at your own risk.'.format(vs_core.version_number()))
        return False

    return True


def patch_dark_stylesheet(stylesheet: str) -> str:
    return stylesheet + 'QGraphicsView { border: 0px; padding: 0px; }'