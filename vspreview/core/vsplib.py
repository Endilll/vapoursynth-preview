from __future__ import annotations

from   abc      import abstractmethod
from   datetime import timedelta
import logging
from   pathlib  import Path
from   typing   import (
    Any, cast, Dict, Iterator, Mapping, no_type_check, Optional,
    overload, Type, TypeVar, TYPE_CHECKING, Tuple, Union,
)

from PyQt5 import Qt, sip
from yaml import (
    add_constructor, add_representer, Dumper, Loader, Node, YAMLObject,
    YAMLObjectMetaclass,
)
from vapoursynth import Format, VideoNode

from .better_abc import ABCMeta, abstract_attribute
# project modules couldn't be imported at top level
# since it'll cause cyclic import

# pylint: disable=pointless-statement, function-redefined

# TODO: consider making FrameInterval non-negative
# TODO: consider storing assosiated Output in Frame and others


class Frame(YAMLObject):
    __slots__ = (
        'value',
    )

    yaml_tag = '!Frame'

    def __init__(self, init_value: Union[Frame, int, Time]) -> None:
        from vspreview.utils import main_window

        if isinstance(init_value, int):
            if init_value < 0:
                raise ValueError
            self.value = init_value
        elif isinstance(init_value, Frame):
            self.value = init_value.value
        elif isinstance(init_value, Time):
            self.value = main_window().current_output.to_frame(
                init_value).value
        else:
            raise TypeError

    def __add__(self, other: FrameInterval) -> Frame:
        return Frame(self.value + other.value)

    def __iadd__(self, other: FrameInterval) -> Frame:
        self.value += other.value
        return self

    @overload
    def __sub__(self, other: FrameInterval) -> Frame: ...
    @overload
    def __sub__(self, other: Frame) -> FrameInterval: ...

    def __sub__(self, other):  # type: ignore
        if isinstance(other, Frame):
            return FrameInterval(self.value - other.value)
        if isinstance(other, FrameInterval):
            return Frame(self.value - other.value)
        raise TypeError

    def __isub__(self, other: FrameInterval) -> Frame:  # type: ignore
        self.value -= other.value
        return self

    def __int__(self) -> int:
        return self.value

    def __index__(self) -> int:
        return int(self)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f'Frame({self.value})'

    def __eq__(self, other: Frame) -> bool:  # type: ignore
        return self.value == other.value

    def __gt__(self, other: Frame) -> bool:
        return self.value > other.value

    def __ne__(self, other: Frame) -> bool:  # type: ignore
        return not self.__eq__(other)

    def __le__(self, other: Frame) -> bool:
        return not self.__gt__(other)

    def __ge__(self, other: Frame) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __lt__(self, other: Frame) -> bool:
        return not self.__ge__(other)


    def __getstate__(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            value = state['value']
            if not isinstance(value, int):
                raise TypeError('Value of Frame isn\'t an integer. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('Frame lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(value)  # type: ignore


class FrameInterval(YAMLObject):
    __slots__ = (
        'value',
    )

    yaml_tag = '!FrameInterval'

    def __init__(self, init_value: Union[FrameInterval, int, TimeInterval]) -> None:
        from vspreview.utils import main_window

        if isinstance(init_value, int):
            self.value = init_value
        elif isinstance(init_value, FrameInterval):
            self.value = init_value.value
        elif isinstance(init_value, TimeInterval):
            self.value = main_window().current_output.to_frame_interval(
                init_value).value
        else:
            raise TypeError

    def __add__(self, other: FrameInterval) -> FrameInterval:
        return FrameInterval(self.value + other.value)

    def __iadd__(self, other: FrameInterval) -> FrameInterval:
        self.value += other.value
        return self

    def __sub__(self, other: FrameInterval) -> FrameInterval:
        return FrameInterval(self.value - other.value)

    def __isub__(self, other: FrameInterval) -> FrameInterval:
        self.value -= other.value
        return self

    def __mul__(self, other: int) -> FrameInterval:
        return FrameInterval(self.value * other)

    def __imul__(self, other: int) -> FrameInterval:
        self.value *= other
        return self

    def __rmul__(self, other: int) -> FrameInterval:
        return FrameInterval(other * self.value)

    def __floordiv__(self, other: float) -> FrameInterval:
        return FrameInterval(int(self.value // other))

    def __ifloordiv__(self, other: float) -> FrameInterval:
        self.value = int(self.value // other)
        return self

    def __int__(self) -> int:
        return self.value

    def __index__(self) -> int:
        return int(self)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f'FrameInterval({self.value})'

    def __eq__(self, other: FrameInterval) -> bool:  # type: ignore
        return self.value == other.value

    def __gt__(self, other: FrameInterval) -> bool:
        return self.value > other.value

    def __ne__(self, other: FrameInterval) -> bool:  # type: ignore
        return not self.__eq__(other)

    def __le__(self, other: FrameInterval) -> bool:
        return not self.__gt__(other)

    def __ge__(self, other: FrameInterval) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __lt__(self, other: FrameInterval) -> bool:
        return not self.__ge__(other)


    def __getstate__(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            value = state['value']
            if not isinstance(value, int):
                raise TypeError('Value of FrameInterval isn\'t an integer. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('FrameInterval lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(value)  # type: ignore


FrameType = TypeVar('FrameType', Frame, FrameInterval)


class Time(YAMLObject):
    __slots__ = (
        'value',
    )

    yaml_tag = '!Time'

    def __init__(self, init_value: Optional[Union[Time, timedelta, Frame]] = None, **kwargs: Any):
        from vspreview.utils import main_window

        if isinstance(init_value, timedelta):
            self.value = init_value
        elif isinstance(init_value, Time):
            self.value = init_value.value
        elif isinstance(init_value, Frame):
            self.value = main_window().current_output.to_time(
                init_value).value
        elif any(kwargs):
            self.value = timedelta(**kwargs)
        elif init_value is None:
            self.value = timedelta()
        else:
            raise TypeError

    def __add__(self, other: TimeInterval) -> Time:
        return Time(self.value + other.value)

    def __iadd__(self, other: TimeInterval) -> Time:
        self.value += other.value
        return self

    @overload
    def __sub__(self, other: TimeInterval) -> Time: ...
    @overload
    def __sub__(self, other: Time) -> TimeInterval: ...

    def __sub__(self, other):  # type: ignore
        if isinstance(other, Time):
            return TimeInterval(self.value - other.value)
        if isinstance(other, TimeInterval):
            return Time(self.value - other.value)
        raise TypeError

    def __isub__(self, other: TimeInterval) -> Time:  # type: ignore
        self.value -= other.value
        return self

    def __str__(self) -> str:
        from vspreview.utils import strfdelta

        return strfdelta(self, '%h:%M:%S.%Z')

    def __repr__(self) -> str:
        return f'Time({self.value})'

    def __eq__(self, other: Time) -> bool:  # type: ignore
        return self.value == other.value

    def __gt__(self, other: Time) -> bool:
        return self.value > other.value

    def __ne__(self, other: Time) -> bool:  # type: ignore
        return not self.__eq__(other)

    def __le__(self, other: Time) -> bool:
        return not self.__gt__(other)

    def __ge__(self, other: Time) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __lt__(self, other: Time) -> bool:
        return not self.__ge__(other)


    def __getstate__(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            value = state['value']
            if not isinstance(value, timedelta):
                raise TypeError('Value of Time isn\'t an timedelta. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('Time lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(value)  # type: ignore


class TimeInterval(YAMLObject):
    __slots__ = (
        'value',
    )

    yaml_tag = '!TimeInterval'

    def __init__(self, init_value: Optional[Union[TimeInterval, timedelta, FrameInterval]] = None, **kwargs: Any):
        from vspreview.utils import main_window

        if isinstance(init_value, timedelta):
            self.value = init_value
        elif isinstance(init_value, TimeInterval):
            self.value = init_value.value
        elif isinstance(init_value, FrameInterval):
            self.value = main_window().current_output.to_time_interval(
                init_value).value
        elif any(kwargs):
            self.value = timedelta(**kwargs)
        elif init_value is None:
            self.value = timedelta()
        else:
            raise TypeError()

    def __add__(self, other: TimeInterval) -> TimeInterval:
        return TimeInterval(self.value + other.value)

    def __iadd__(self, other: TimeInterval) -> TimeInterval:
        self.value += other.value
        return self

    def __sub__(self, other: TimeInterval) -> TimeInterval:
        return TimeInterval(self.value - other.value)

    def __isub__(self, other: TimeInterval) -> TimeInterval:
        self.value -= other.value
        return self

    def __mul__(self, other: int) -> TimeInterval:
        return TimeInterval(self.value * other)

    def __imul__(self, other: int) -> TimeInterval:
        self.value *= other
        return self

    def __rmul__(self, other: int) -> TimeInterval:
        return TimeInterval(other * self.value)

    def __truediv__(self, other: float) -> TimeInterval:
        return TimeInterval(self.value / other)

    def __itruediv__(self, other: float) -> TimeInterval:
        self.value /= other
        return self

    def __str__(self) -> str:
        from vspreview.utils import strfdelta

        return strfdelta(self, '%h:%M:%S.%Z')

    def __repr__(self) -> str:
        return f'TimeInterval({self.value})'

    def __eq__(self, other: TimeInterval) -> bool:  # type: ignore
        return self.value == other.value

    def __gt__(self, other: TimeInterval) -> bool:
        return self.value > other.value

    def __ne__(self, other: TimeInterval) -> bool:  # type: ignore
        return not self.__eq__(other)

    def __le__(self, other: TimeInterval) -> bool:
        return not self.__gt__(other)

    def __ge__(self, other: TimeInterval) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __lt__(self, other: TimeInterval) -> bool:
        return not self.__ge__(other)


    def __getstate__(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            value = state['value']
            if not isinstance(value, timedelta):
                raise TypeError('Value of TimeInterval isn\'t an timedelta. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('TimeInterval lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(value)  # type: ignore


TimeType = TypeVar('TimeType', Time, TimeInterval)


class Scene(YAMLObject):
    __slots__ = (
        'start', 'end', 'label'
    )

    yaml_tag = '!Scene'

    def __init__(self, start: Optional[Frame] = None, end: Optional[Frame] = None, label: str = '') -> None:
        if start is not None and end is not None:
            self.start = start
            self.end   = end
        elif start is not None:
            self.start = start
            self.end   = start
        elif end is not None:
            self.start = end
            self.end   = end
        else:
            raise ValueError

        if self.start > self.end:
            self.start, self.end = self.end, self.start

        self.label = label

    def __str__(self) -> str:
        result = ''

        if self.start == self.end:
            result = f'{self.start}'
        else:
            result = f'{self.start} - {self.end}'

        if self.label != '':
            result += f': {self.label}'

        return result

    def __repr__(self) -> str:
        return 'Scene({}, {}, \'{}\')'.format(self.start, self.end, self.label)

    def __eq__(self, other: Scene) -> bool:  # type: ignore
        return self.start == other.start and self.end == other.end

    def __gt__(self, other: Scene) -> bool:
        if self.start != other.start:
            return self.start > other.start
        else:
            return self.end   > other.end

    def __ne__(self, other: Scene) -> bool:  # type: ignore
        return not self.__eq__(other)

    def __le__(self, other: Scene) -> bool:
        return not self.__gt__(other)

    def __ge__(self, other: Scene) -> bool:
        return self.__eq__(other) or self.__gt__(other)

    def __lt__(self, other: Scene) -> bool:
        return not self.__ge__(other)

    def duration(self) -> FrameInterval:
        return self.end - self.start

    def __contains__(self, frame: Frame) -> bool:
        return self.start <= frame <= self.end

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            start = state['start']
            if not isinstance(start, Frame):
                raise TypeError('Start frame of Scene is not a Frame. It\'s most probably corrupted.')

            end = state['end']
            if not isinstance(end, Frame):
                raise TypeError('End frame of Scene is not a Frame. It\'s most probably corrupted.')

            label = state['label']
            if not isinstance(label, str):
                raise TypeError('Label of Scene is not a string. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('Scene lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(start, end, label)  # type: ignore


class Output(YAMLObject):
    storable_attrs = (
        'name', 'last_showed_frame', 'scening_lists', 'play_fps'
    )
    __slots__ = storable_attrs + (
        'vs_output', 'index', 'width', 'height', 'fps_num', 'fps_den',
        'format', 'total_frames', 'total_time', 'graphics_scene_item',
        'end_frame', 'end_time', 'fps'
    )

    yaml_tag = '!Output'

    def __init__(self, vs_output: VideoNode, index: int, pixel_format: Format) -> None:
        from vspreview.models import SceningLists

        # runtime attributes

        self.vs_output    = vs_output
        self.index        = index
        self.width        = self.vs_output.width
        self.height       = self.vs_output.height
        self.fps_num      = self.vs_output.fps.numerator
        self.fps_den      = self.vs_output.fps.denominator
        self.fps          = self.fps_num / self.fps_den
        self.format       = pixel_format
        self.total_frames = FrameInterval(self.vs_output.num_frames)
        self.total_time   = self.to_time_interval(self.total_frames - FrameInterval(1))
        self.end_frame    = Frame(self.total_frames.value - 1)
        self.end_time     = self.to_time(self.end_frame)

        # set by load_script() when it prepares graphics scene item
        # based on last showed frame

        self.graphics_scene_item: Qt.QGraphicsPixmapItem

        # storable attributes

        if not hasattr(self, 'name'):
            self.name = 'Output ' + str(self.index)
        if (not hasattr(self, 'last_showed_frame')
                or self.last_showed_frame > self.end_frame):
            self.last_showed_frame: Frame = Frame(0)
        if not hasattr(self, 'scening_lists'):
            self.scening_lists: SceningLists = SceningLists()
        if not hasattr(self, 'play_fps'):
            self.play_fps = self.fps_num / self.fps_den

    def _calculate_frame(self, seconds: float) -> int:
        return round(seconds * self.fps)

    def _calculate_seconds(self, frame_num: int) -> float:
        return frame_num / self.fps

    def to_frame(self, time: Time) -> Frame:
        return Frame(self._calculate_frame(time.value.total_seconds()))

    def to_time(self, frame: Frame) -> Time:
        return Time(seconds=self._calculate_seconds(int(frame)))

    def to_frame_interval(self, time_interval: TimeInterval) -> FrameInterval:
        return FrameInterval(self._calculate_frame(time_interval.value.total_seconds()))

    def to_time_interval(self, frame_interval: FrameInterval) -> TimeInterval:
        return TimeInterval(seconds=self._calculate_seconds(int(frame_interval)))

    def __getstate__(self) -> Mapping[str, Any]:
        return {attr_name: getattr(self, attr_name)
                for attr_name in self.storable_attrs}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            name = state['name']
            if not isinstance(name, str):
                raise TypeError
            self.name = name
        except (KeyError, TypeError):
            logging.warning(f'Storage loading: output {self.index}: failed to parse name.')

        try:
            self.last_showed_frame = state['last_showed_frame']
        except (KeyError, TypeError):
            logging.warning(f'Storage loading: Output: failed to parse last showed frame.')
        except IndexError:
            logging.warning(f'Storage loading: Output: last showed frame is out of range.')

        try:
            self.scening_lists = state['scening_lists']
        except (KeyError, TypeError):
            logging.warning(f'Storage loading: Output: scening lists weren\'t parsed successfully.')

        try:
            play_fps = state['play_fps']
            if not isinstance(play_fps, float):
                raise TypeError
            if play_fps >= 1.0:
                self.play_fps = play_fps
        except (KeyError, TypeError):
            logging.warning(f'Storage loading: Output: play fps weren\'t parsed successfully.')


T = TypeVar('T')


class SingletonMeta(type):
    def __init__(cls: Type[T], name: str, bases: Tuple[type, ...], dct: Dict[str, Any]) -> None:
        super().__init__(name, bases, dct)
        cls.instance: Optional[T] = None  # type: ignore

    def __call__(cls, *args: Any, **kwargs: Any) -> T:
        if cls.instance is None:
            cls.instance = super().__call__(*args, **kwargs)
        return cls.instance

    def __new__(cls: Type[type], name: str, bases: Tuple[type, ...], dct: Dict[str, Any]) -> type:
        subcls = super(SingletonMeta, cls).__new__(cls, name, bases, dct)
        singleton_new = None
        for entry in subcls.__mro__:
            if entry.__class__ is SingletonMeta:
                singleton_new = entry.__new__
        if subcls.__new__ is not singleton_new:
            subcls.__default_new__ = subcls.__new__  # type: ignore
            subcls.__new__ = singleton_new  # type: ignore
        return subcls
class Singleton(metaclass=SingletonMeta):
    @no_type_check
    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls.instance is None:
            if hasattr(cls, '__default_new__'):
                cls.instance = cls.__default_new__(cls, *args, **kwargs)  # pylint: disable=no-member
            else:
                cls.instance = super(Singleton, cls).__new__(cls)
        return cls.instance

class AbstractYAMLObjectMeta(YAMLObjectMetaclass, ABCMeta):
    pass
class AbstractYAMLObject(YAMLObject, metaclass=AbstractYAMLObjectMeta):
    pass

class AbstractYAMLObjectSingletonMeta(SingletonMeta, AbstractYAMLObjectMeta):
    pass
class AbstractYAMLObjectSingleton(AbstractYAMLObject, Singleton, metaclass=AbstractYAMLObjectSingletonMeta):
    pass

class QABCMeta(sip.wrappertype, ABCMeta):  # type: ignore
    pass
class QABC(metaclass=QABCMeta):
    pass

class QSingletonMeta(SingletonMeta, sip.wrappertype):  # type: ignore
    pass
class QSingleton(Singleton, metaclass=QSingletonMeta):
    pass

class QAbstractSingletonMeta(QSingletonMeta, QABCMeta):
    pass
class QAbstractSingleton(Singleton, metaclass=QAbstractSingletonMeta):
    pass

class QYAMLObjectMeta(YAMLObjectMetaclass, sip.wrappertype):  # type: ignore
    pass
class QYAMLObject(YAMLObject, metaclass=QYAMLObjectMeta):
    pass

class QAbstractYAMLObjectMeta(QYAMLObjectMeta, QABC):
    pass
class QAbstractYAMLObject(YAMLObject, metaclass=QAbstractYAMLObjectMeta):
    pass

class QYAMLObjectSingletonMeta(QSingletonMeta, QYAMLObjectMeta):
    pass
class QYAMLObjectSingleton(QYAMLObject, Singleton, metaclass=QYAMLObjectSingletonMeta):
    pass

class QAbstractYAMLObjectSingletonMeta(QYAMLObjectSingletonMeta, QABCMeta):
    pass
class QAbstractYAMLObjectSingleton(QYAMLObjectSingleton, metaclass=QAbstractYAMLObjectSingletonMeta):
    pass


class AbstractMainWindow(Qt.QMainWindow, QAbstractYAMLObjectSingleton):
    if TYPE_CHECKING:
        from vspreview.models  import Outputs
        from vspreview.widgets import Timeline

    __slots__ = ()

    @abstractmethod
    def load_script(self, script_path: Path) -> None:
        raise NotImplementedError()

    @abstractmethod
    def reload_script(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def init_outputs(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def switch_output(self, value: Union[int, Output]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def switch_frame(self, frame: Optional[Frame] = None, time: Optional[Time] = None, *, render_frame: bool = True) -> None:
        raise NotImplementedError()

    central_widget: Qt.QWidget        = abstract_attribute()
    clipboard     : Qt.QClipboard     = abstract_attribute()
    current_frame : Frame             = abstract_attribute()
    current_output: Output            = abstract_attribute()
    display_scale : float             = abstract_attribute()
    graphics_scene: Qt.QGraphicsScene = abstract_attribute()
    graphics_view : Qt.QGraphicsView  = abstract_attribute()
    outputs       : Outputs           = abstract_attribute()
    timeline      : Timeline          = abstract_attribute()
    toolbars      : AbstractToolbars  = abstract_attribute()  # pylint: disable=used-before-assignment
    save_on_exit  : bool              = abstract_attribute()
    script_path   : Path              = abstract_attribute()
    statusbar     : Qt.QStatusBar     = abstract_attribute()


class AbstractToolbar(Qt.QWidget, QABC):
    if TYPE_CHECKING:
        from vspreview.widgets import Notches

    __slots__ = (
        'main', 'toggle_button'
    )

    if TYPE_CHECKING:
        notches_changed = Qt.pyqtSignal(AbstractToolbar)  # pylint: disable=undefined-variable
    else:
        notches_changed = Qt.pyqtSignal(object)

    def __init__(self, main: AbstractMainWindow, name: str) -> None:
        super().__init__(main.central_widget)
        self.main = main

        self.setFocusPolicy(Qt.Qt.ClickFocus)

        self.notches_changed.connect(self.main.timeline.update_notches)

        self.toggle_button = Qt.QPushButton(self)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setText(name)
        self.toggle_button.clicked.connect(self.on_toggle)

        self.setVisible(False)


    def on_toggle(self, new_state: bool) -> None:
        # invoking order matters
        self.setVisible(new_state)
        self.resize_main_window(new_state)

    def on_current_frame_changed(self, frame: Frame, time: Time) -> None:
        pass

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        pass


    def get_notches(self) -> Notches:
        from vspreview.widgets import Notches

        return Notches()

    def is_notches_visible(self) -> bool:
        return self.isVisible()

    def resize_main_window(self, expanding: bool) -> None:
        if self.main.windowState() in (Qt.Qt.WindowMaximized,
                                       Qt.Qt.WindowFullScreen):
            return

        if expanding:
            self.main.resize(self.main.width(), self.main.height() + self.height() + round(6 * self.main.display_scale))
        if not expanding:
            self.main.resize(self.main.width(), self.main.height() - self.height() - round(6 * self.main.display_scale))
            self.main.timeline.full_repaint()

    def __getstate__(self) -> Mapping[str, Any]:
        return {}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        pass


class AbstractToolbars(AbstractYAMLObjectSingleton):
    __slots__ = ()

    yaml_tag: str = abstract_attribute()

    # special toolbar ignored by len() and not accessible via subscription and 'in' operator
    main     : AbstractToolbar = abstract_attribute()

    playback : AbstractToolbar = abstract_attribute()
    scening  : AbstractToolbar = abstract_attribute()
    misc     : AbstractToolbar = abstract_attribute()
    debug    : AbstractToolbar = abstract_attribute()

    toolbars_names = ('playback', 'scening', 'misc', 'debug')
    # 'main' should be the first
    all_toolbars_names = ['main'] + list(toolbars_names)

    def __getitem__(self, index: int) -> AbstractToolbar:
        if index >= len(self.toolbars_names):
            raise IndexError()
        return cast(AbstractToolbar, getattr(self, self.toolbars_names[index]))

    def __len__(self) -> int:
        return len(self.toolbars_names)

    @abstractmethod
    def __getstate__(self) -> Mapping[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    def __setstate__(self, state: Mapping[str, Any]) -> None:
        raise NotImplementedError()

    if TYPE_CHECKING:
        # https://github.com/python/mypy/issues/2220
        def __iter__(self) -> Iterator[AbstractToolbar]: ...
