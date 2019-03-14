from __future__ import annotations

from   abc       import abstractmethod
from   datetime  import timedelta
from   functools import total_ordering
import logging
from   pathlib   import Path
from   typing    import Any, cast, Dict, Iterator, Mapping, no_type_check, Optional, Type, TypeVar, TYPE_CHECKING, Tuple, Union

from PyQt5       import Qt, sip  # type: ignore
from yaml        import add_constructor, add_representer, Dumper, Loader, Node, YAMLObject, YAMLObjectMetaclass
from vapoursynth import Format, VideoNode

from .better_abc  import ABCMeta, abstract_attribute
# project modules couldn't be imported at top level since it'll cause cyclic import


class Frame(int):
    yaml_tag = '!Frame'

    def __radd__(self, other: Any) -> Frame:
        return Frame(super().__radd__(other))

    def __add__(self, other: Any) -> Frame:
        return Frame(super().__add__(other))

    def __sub__(self, other: Any) -> Frame:
        return Frame(super().__sub__(other))

    @classmethod
    def from_yaml(cls: Any, loader: Loader, node: Node) -> Frame:
        return Frame(loader.construct_scalar(node))

    @classmethod
    def to_yaml(cls: Any, dumper: Dumper, instance: Frame) -> Node:
        return dumper.represent_scalar(cls.yaml_tag, str(instance))


add_constructor(Frame.yaml_tag, Frame.from_yaml)
add_representer(Frame,          Frame.  to_yaml)


@total_ordering
class Scene(YAMLObject):
    __slots__ = (
        'start', 'end', 'label'
    )

    yaml_tag = '!Scene'

    def __init__(self, start: Frame, end: Optional[Frame] = None, label: str = '') -> None:
        if end is None:
            self.start = start
            self.end   = start
        elif start <= end:
            self.start = start
            self.end   = end
        else:
            self.start = end
            self.end   = start

        self.label = label

    def __str__(self) -> str:
        if self.start == self.end:
            part_1 = f'{self.start}'
        else:
            part_1 = f'{self.start} - {self.end}'

        if self.label == '':
            part_2 = f': {self.label}'
        else:
            part_2 = ''

        return part_1 + part_2

    def __gt__(self, other: Scene) -> bool:
        if self.start != other.start:
            return self.start > other.start
        else:
            return self.end   > other.end

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Scene):
            raise TypeError
        return self.start == other.start and self.end == other.end

    def duration(self) -> int:
        return self.end - self.start

    def __contains__(self, frame: Frame) -> bool:
        if not isinstance(frame, Frame):
            raise TypeError
        return self.start <= frame <= self.end

    def __getstate__(self) -> Mapping[str, Any]:
        return {name: getattr(self, name)
                for name in self.__slots__}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            start = state['start']
            if not isinstance(start, Frame):
                raise TypeError('Start frame of Scene is not a Frame. It\'s most probably corrupted.')

            end = state['end']
            if not isinstance(end, Frame):
                raise TypeError('End frame of Scene is not a Frame. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('Scene lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(start, end)  # type: ignore

    # @classmethod
    # def from_yaml(cls: Any, loader: Loader, node: Node) -> Scene:
    #     string = loader.construct_scalar(node)
    #     start, end = map(Frame, string.split(' - '))
    #     return Scene(start, end)  # type: ignore

    # @classmethod
    # def to_yaml(cls: Any, dumper: Dumper, instance: Scene) -> Node:
    #     return dumper.represent_scalar(cls.yaml_tag, str(instance))  # type: ignore


@total_ordering
class Bookmark(YAMLObject):
    __slots__ = (
        'frame', 'label'
    )

    yaml_tag = '!Bookmark'

    def __init__(self, frame: Frame, label: str = '') -> None:
        self.frame = frame
        self.label = label

    def __eq__(self, other: Union[Bookmark, Frame]) -> bool:  # type: ignore
        if isinstance(other, Bookmark):
            return self.frame == other.frame and self.label == other.label
        if isinstance(other, Frame):
            return self.frame == other

        logging.debug(type(other))
        raise TypeError()

    def __ge__(self, other: Union[Bookmark, Frame]) -> bool:
        if isinstance(other, Bookmark):
            if self.frame != other.frame:
                return self.frame >= other.frame
            else:
                return len(self.label) >= len(other.label)
        if isinstance(other, Frame):
            return self.frame >= other

        logging.debug(type(other))
        raise TypeError()

    def __getstate__(self) -> Mapping[str, Any]:
        return {name: getattr(self, name)
                for name in self.__slots__}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            frame = state['frame']
            if not isinstance(frame, Frame):
                raise TypeError('\'frame\' of a Bookmark is not a Frame. It\'s most probably corrupted.')

            label = state['label']
            if not isinstance(label, str):
                raise TypeError('\'label\' of a Bookmark is not a Frame. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('Bookmark lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(frame, label)  # type: ignore


class Output(YAMLObject):
    storable_attrs = (
        'name', 'last_showed_frame', 'bookmarks', 'scening_lists', 'play_fps'
    )
    __slots__ = storable_attrs + (
        'vs_output', 'index', 'width', 'height', 'fps_num', 'fps_den',
        'format', 'total_frames', 'duration', 'graphics_scene_item'
    )

    yaml_tag = '!Output'

    def __init__(self, vs_output: VideoNode, index: int, pixel_format: Format) -> None:
        from vspreview.toolbars.bookmarks import Bookmarks
        from vspreview.toolbars.scening   import SceningLists

        # runtime attributes

        self.vs_output    = vs_output
        self.index        = index
        self.width        = self.vs_output.width
        self.height       = self.vs_output.height
        self.fps_num      = self.vs_output.fps.numerator
        self.fps_den      = self.vs_output.fps.denominator
        self.format       = pixel_format
        self.total_frames = Frame(self.vs_output.num_frames)
        self.duration     = timedelta(seconds=(self.total_frames / (self.fps_num / self.fps_den)))

        # set by load_script() when it prepares graphics scene item based on last showed frame

        self.graphics_scene_item: Qt.QGraphicsPixmapItem

        # storable attributes

        if not hasattr(self, 'name'):
            self.name = 'Output ' + str(self.index)
        if (not hasattr(self, 'last_showed_frame')
                or self.last_showed_frame >= self.total_frames):
            self.last_showed_frame: Frame = Frame(0)
        if not hasattr(self, 'bookmarks'):
            self.bookmarks: Bookmarks = Bookmarks(self.total_frames - 1)
        if not hasattr(self, 'scening_lists'):
            self.scening_lists: SceningLists = SceningLists(self.total_frames - 1)
        if not hasattr(self, 'play_fps'):
            self.play_fps = self.fps_num / self.fps_den

    def __getstate__(self) -> Mapping[str, Any]:
        return {attr_name: getattr(self, attr_name)
                for attr_name in self.storable_attrs}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            name = state['name']
            if not isinstance(name, str):
                raise TypeError()
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
            self.bookmarks = state['bookmarks']
        except (KeyError, TypeError, ValueError):
            logging.warning(f'Storage loading: Output: failed to parse bookmarks.')

        try:
            self.scening_lists = state['scening_lists']
        except (KeyError, TypeError):
            logging.warning(f'Storage loading: Output: scening lists weren\'t parsed successfully.')

        try:
            play_fps = state['play_fps']
            if not isinstance(play_fps, float):
                raise TypeError()
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
    def switch_output(self, index: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    def on_current_frame_changed(self, frame: Optional[Frame] = None, t: Optional[timedelta] = None, render_frame: bool = True) -> None:
        raise NotImplementedError()

    @abstractmethod
    def frame_to_timedelta(self, frame: Frame) -> timedelta:
        raise NotImplementedError()

    @abstractmethod
    def timedelta_to_frame(self, t: timedelta) -> Frame:
        raise NotImplementedError()

    display_scale : float             = abstract_attribute()
    central_widget: Qt.QWidget        = abstract_attribute()
    clipboard     : Qt.QClipboard     = abstract_attribute()
    current_frame : Frame             = abstract_attribute()
    current_output: Output            = abstract_attribute()
    graphics_scene: Qt.QGraphicsScene = abstract_attribute()
    graphics_view : Qt.QGraphicsView  = abstract_attribute()
    save_on_exit  : bool              = abstract_attribute()
    script_path   : Path              = abstract_attribute()
    statusbar     : Qt.QStatusBar     = abstract_attribute()
    outputs       : Outputs           = abstract_attribute()
    timeline      : Timeline          = abstract_attribute()
    toolbars      : AbstractToolbars  = abstract_attribute()  # pylint: disable=used-before-assignment


class AbstractToolbar(Qt.QWidget, QABC):
    __slots__ = ('main')

    if not TYPE_CHECKING:
        timelineMarksChanged = Qt.pyqtSignal(object)
    else:
        timelineMarksChanged = Qt.pyqtSignal(AbstractToolbar)  # pylint: disable=undefined-variable

    def __init__(self, main_window: AbstractMainWindow) -> None:
        self.main = main_window
        super().__init__(self.main.central_widget)

        self.timelineMarksChanged.connect(self.main.timeline.updateTimelineMarks)

    @abstractmethod
    def on_toggle(self, new_state: bool) -> None:
        raise NotImplementedError()

    @abstractmethod
    def on_current_frame_changed(self, frame: Frame, t: timedelta) -> None:
        raise NotImplementedError()

    @abstractmethod
    def on_current_output_changed(self, index: int) -> None:
        raise NotImplementedError()

    def resize_main_window(self, expanding: bool) -> None:
        if expanding:
            self.main.resize(self.main.width(), self.main.height() + self.height() + round(6 * self.main.display_scale))
        if not expanding:
            self.main.resize(self.main.width(), self.main.height() - self.height() - round(6 * self.main.display_scale))
            self.main.timeline.needFullRepaint = True

    def __getstate__(self) -> Mapping[str, Any]:
        return {}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        pass


class AbstractToolbars(AbstractYAMLObjectSingleton):
    __slots__ = ()

    yaml_tag: str = abstract_attribute()

    # special toolbar ignored by len and not accessible via supscription and 'in' operator
    main     : AbstractToolbar = abstract_attribute()

    playback : AbstractToolbar = abstract_attribute()
    bookmarks: AbstractToolbar = abstract_attribute()
    scening  : AbstractToolbar = abstract_attribute()
    misc     : AbstractToolbar = abstract_attribute()

    toolbars_names = ('playback', 'bookmarks', 'scening', 'misc')
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
        def __iter__(self) -> Iterator[AbstractToolbar]:
            ...  # pylint: disable=pointless-statement
