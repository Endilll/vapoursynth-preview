from __future__ import annotations

# pylint: disable=function-redefined,pointless-statement

from datetime import timedelta
from typing   import (
    Any, Optional, overload, TypeVar, Union,
)

from PySide2.QtGui import QImage, QPixmap

from vapoursynth import core as vs_core, VideoNode


class Frame:
    __slots__ = (
        'value',
    )

    def __init__(self, init_value: Union[Frame, int, Time]) -> None:
        from vspreview.utils import main_view_model

        if isinstance(init_value, int):
            if init_value < 0:
                raise ValueError
            self.value = init_value
        elif isinstance(init_value, Frame):
            self.value = init_value.value
        elif isinstance(init_value, Time):
            self.value = main_view_model().current_output.to_frame(
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

    def __float__(self) -> float:
        return float(self.value)

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

class FrameInterval:
    __slots__ = (
        'value',
    )

    def __init__(self, init_value: Union[FrameInterval, int, TimeInterval]) -> None:
        from vspreview.utils import main_view_model

        if isinstance(init_value, int):
            self.value = init_value
        elif isinstance(init_value, FrameInterval):
            self.value = init_value.value
        elif isinstance(init_value, TimeInterval):
            self.value = main_view_model().current_output.to_frame_interval(
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

    def __float__(self) -> float:
        return float(self.value)

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

FrameType = TypeVar('FrameType', Frame, FrameInterval)


class Time:
    __slots__ = (
        'value',
    )

    def __init__(self, init_value: Optional[Union[Time, timedelta, Frame]] = None, **kwargs: Any):
        from vspreview.utils import main_view_model

        if isinstance(init_value, timedelta):
            self.value = init_value
        elif isinstance(init_value, Time):
            self.value = init_value.value
        elif isinstance(init_value, Frame):
            self.value = main_view_model().current_output.to_time(
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

    def __float__(self) -> float:
        return self.value.total_seconds()

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

class TimeInterval:
    __slots__ = (
        'value',
    )

    def __init__(self, init_value: Optional[Union[TimeInterval, timedelta, FrameInterval]] = None, **kwargs: Any):
        from vspreview.utils import main_view_model

        if isinstance(init_value, timedelta):
            self.value = init_value
        elif isinstance(init_value, TimeInterval):
            self.value = init_value.value
        elif isinstance(init_value, FrameInterval):
            self.value = main_view_model().current_output.to_time_interval(
                init_value).value
        elif any(kwargs):
            self.value = timedelta(**kwargs)
        elif init_value is None:
            self.value = timedelta()
        else:
            raise TypeError

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

    def __float__(self) -> float:
        return self.value.total_seconds()

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

TimeType = TypeVar('TimeType', Time, TimeInterval)


class Scene:
    __slots__ = (
        'start', 'end', 'label'
    )

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


class Output:
    from .customized import GraphicsItem

    class Resizer:
        Bilinear = vs_core.resize.Bilinear
        Bicubic  = vs_core.resize.Bicubic
        Point    = vs_core.resize.Point
        Lanczos  = vs_core.resize.Lanczos
        Spline16 = vs_core.resize.Spline16
        Spline36 = vs_core.resize.Spline36

    class Matrix:
        values = {
            0:  'rgb',
            1:  '709',
            2:  'unspec',
            # 3:  'reserved',
            4:  'fcc',
            5:  '470bg',
            6:  '170m',
            7:  '240m',
            8:  'ycgco',
            9:  '2020ncl',
            10: '2020cl',
            # 11: 'reserved',
            12: 'chromancl',
            13: 'chromacl',
            14: 'ictcp',
        }

        RGB        = values[ 0]
        BT709      = values[ 1]
        UNSPEC     = values[ 2]
        BT470_BG   = values[ 5]
        ST170_M    = values[ 6]
        ST240_M    = values[ 7]
        FCC        = values[ 4]
        YCGCO      = values[ 8]
        BT2020_NCL = values[ 9]
        BT2020_CL  = values[10]
        CHROMA_CL  = values[13]
        CHROMA_NCL = values[12]
        ICTCP      = values[14]

    class Transfer:
        values = {
            # 0:  'reserved',
            1:  '709',
            2:  'unspec',
            # 3:  'reserved',
            4:  '470m',
            5:  '470bg',
            6:  '601',
            7:  '240m',
            8:  'linear',
            9:  'log100',
            10: 'log316',
            11: 'xvycc',  # IEC 61966-2-4
            # 12: 'reserved',
            13: 'srgb',  # IEC 61966-2-1
            14: '2020_10',
            15: '2020_12',
            16: 'st2084',
            # 17: 'st428',  # not supported by zimg 2.8
            18: 'std-b67',
        }

        BT709         = values[ 1]
        UNSPEC        = values[ 2]
        BT601         = values[ 6]
        LINEAR        = values[ 8]
        BT2020_10     = values[14]
        BT2020_12     = values[15]
        ST240_M       = values[ 7]
        BT470_M       = values[ 4]
        BT470_BG      = values[ 5]
        LOG_100       = values[ 9]
        LOG_316       = values[10]
        ST2084        = values[16]
        ARIB_B67      = values[18]
        SRGB          = values[13]
        XV_YCC        = values[11]
        IEC_61966_2_4 = XV_YCC
        IEC_61966_2_1 = SRGB

    class Primaries:
        values = {
            # 0:  'reserved',
            1:  '709',
            2:  'unspec',
            # 3:  'reserved',
            4:  '470m',
            5:  '470bg',
            6:  '170m',
            7:  '240m',
            8:  'film',
            9:  '2020',
            10: 'st428',  # or 'xyz'
            11: 'st431-2',
            12: 'st431-1',
            22: 'jedec-p22',
        }

        BT709     = values[ 1]
        UNSPEC    = values[ 2]
        ST170_M   = values[ 6]
        ST240_M   = values[ 7]
        BT470_M   = values[ 4]
        BT470_BG  = values[ 5]
        FILM      = values[ 8]
        BT2020    = values[ 9]
        ST428     = values[10]
        XYZ       = ST428
        ST431_2   = values[11]
        ST431_1   = values[12]
        JEDEC_P22 = values[22]
        EBU3213_E = JEDEC_P22

    class Range:
        values = {
            0: 'full',
            1: 'limited'
        }

        LIMITED = values[1]
        FULL    = values[0]

    class ChromaLoc:
        values = {
            0: 'left',
            1: 'center',
            2: 'top_left',
            3: 'top',
            4: 'bottom_left',
            5: 'bottom',
        }

        LEFT        = values[0]
        CENTER      = values[1]
        TOP_LEFT    = values[2]
        TOP         = values[3]
        BOTTOM_LEFT = values[4]
        BOTTOM      = values[5]

    __slots__ = (
        'vs_output', 'index', 'width', 'height', 'fps_num', 'fps_den',
        'format', 'total_frames', 'total_time', '_graphics_item',
        'end_frame', 'end_time', 'fps', '_current_frame', '_name',
        '__weakref__',
    )

    def __init__(self, vs_output: VideoNode, index: int) -> None:
        from .customized import GraphicsItem

        self.format       = vs_output.format  # changed after preparing vs ouput
        self.index        = index
        self.vs_output    = self.prepare_vs_output(vs_output)
        self.width        = self.vs_output.width
        self.height       = self.vs_output.height
        self.fps_num      = self.vs_output.fps.numerator
        self.fps_den      = self.vs_output.fps.denominator
        self.fps          = self.fps_num / self.fps_den
        self.total_frames = FrameInterval(self.vs_output.num_frames)
        self.total_time   = self.to_time_interval(self.total_frames - FrameInterval(1))
        self.end_frame   = Frame(int(self.total_frames) - 1)
        self.end_time    = self.to_time(self.end_frame)

        self._graphics_item: Optional[GraphicsItem] = None
        self._current_frame = Frame(0)
        self._name = f'Output {self.index}'

    def prepare_vs_output(self, vs_output: VideoNode) -> VideoNode:
        from vapoursynth import COMPATBGR32, RGB
        from vspreview import settings

        resizer = settings.VS_OUTPUT_RESIZER
        resizer_kwargs = {
            'format'        : COMPATBGR32,
            'matrix_in_s'   : settings.VS_OUTPUT_MATRIX,
            'transfer_in_s' : settings.VS_OUTPUT_TRANSFER,
            'primaries_in_s': settings.VS_OUTPUT_PRIMARIES,
            'range_in_s'    : settings.VS_OUTPUT_RANGE,
            'chromaloc_in_s': settings.VS_OUTPUT_CHROMALOC,
            'prefer_props'  : settings.VS_OUTPUT_PREFER_PROPS,
        }

        vs_output = vs_core.std.FlipVertical(vs_output)

        if vs_output.format == COMPATBGR32:  # type: ignore
            return vs_output

        is_subsampled = vs_output.format.subsampling_w != 0 or vs_output.format.subsampling_h != 0
        if not is_subsampled:
            resizer = self.Resizer.Point
        if vs_output.format.color_family == RGB:
            del resizer_kwargs['matrix_in_s']

        vs_output = resizer(vs_output, **resizer_kwargs, **settings.VS_OUTPUT_RESIZER_KWARGS)

        return vs_output

    def __getitem__(self, frame: Frame) -> QPixmap:
        if frame < Frame(0) or frame > self.end_frame:
            raise IndexError
        return self.render_frame(frame)

    def __len__(self) -> int:  # pylint: disable=invalid-length-returned
        return int(self.total_frames)

    @property
    def current_frame(self) -> Frame:
        return self._current_frame
    @current_frame.setter
    def current_frame(self, new_frame: Frame) -> None:
        if self.graphics_item is not None and self.graphics_item.visible:
            self.graphics_item.setPixmap(self[new_frame])
        self._current_frame = new_frame

    @property
    def graphics_item(self) -> Optional[GraphicsItem]:
        return self._graphics_item
    @graphics_item.setter
    def graphics_item(self, new_item: Optional[GraphicsItem]) -> None:
        if new_item is not None:
            ret = new_item.about_to_show.connect(lambda: new_item.setPixmap(self[self.current_frame])); assert ret
        self._graphics_item = new_item

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return '{} \'{}\''.format(type(self).__name__, self._name)

    def render_frame(self, frame: Frame) -> QPixmap:
        import ctypes

        vs_frame = self.vs_output.get_frame(int(frame))

        frame_pointer  = vs_frame.get_read_ptr(0)
        frame_stride   = vs_frame.get_stride(0)
        frame_itemsize = vs_frame.format.bytes_per_sample

        data_pointer = ctypes.cast(
            frame_pointer,
            ctypes.POINTER(ctypes.c_char * (frame_itemsize * vs_frame.width * vs_frame.height))
        )[0]
        frame_image  = QImage(data_pointer, vs_frame.width, vs_frame.height, frame_stride, QImage.Format_RGB32)
        frame_pixmap = QPixmap.fromImage(frame_image)

        return frame_pixmap

    def _calculate_frame(self, seconds: float) -> int:
        return round(seconds * self.fps)

    def _calculate_seconds(self, frame_num: int) -> float:
        return frame_num / self.fps

    def to_frame(self, time: Time) -> Frame:
        return Frame(self._calculate_frame(float(time)))

    def to_time(self, frame: Frame) -> Time:
        return Time(seconds=self._calculate_seconds(int(frame)))

    def to_frame_interval(self, time_interval: TimeInterval) -> FrameInterval:
        return FrameInterval(self._calculate_frame(float(time_interval)))

    def to_time_interval(self, frame_interval: FrameInterval) -> TimeInterval:
        return TimeInterval(seconds=self._calculate_seconds(int(frame_interval)))
