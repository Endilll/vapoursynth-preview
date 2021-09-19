from __future__ import annotations

from   bisect   import bisect_left, bisect_right
import logging
from   typing   import (
    Any, Callable, cast, Dict, Iterator, List, Mapping, Optional, Set, Tuple,
    Union,
)

from PyQt5 import Qt

from vspreview.core import (
    Frame, FrameInterval, QYAMLObject,
    Scene, Time, TimeInterval,
)
from vspreview.utils import debug, main_window


class SceningList(Qt.QAbstractTableModel, QYAMLObject):
    yaml_tag = '!SceningList'

    __slots__ = (
        'name', 'items',
    )

    START_FRAME_COLUMN = 0
    END_FRAME_COLUMN   = 1
    START_TIME_COLUMN  = 2
    END_TIME_COLUMN    = 3
    LABEL_COLUMN       = 4
    COLUMN_COUNT       = 5

    def __init__(self, name: str = '', items: Optional[List[Scene]] = None, vfr: bool = False) -> None:
        super().__init__()
        self.name  = name
        self.items = items if items is not None else []

        self.main = main_window()

    def rowCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        return len(self.items)

    def columnCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        return self.COLUMN_COUNT

    def headerData(self, section: int, orientation: Qt.Qt.Orientation, role: int = Qt.Qt.DisplayRole) -> Any:
        if role != Qt.Qt.DisplayRole:
            return None

        if orientation == Qt.Qt.Horizontal:
            if section == self.START_FRAME_COLUMN:
                return 'Start'
            if section == self.END_FRAME_COLUMN:
                return 'End'
            if section == self.START_TIME_COLUMN:
                return 'Start'
            if section == self.END_TIME_COLUMN:
                return 'End'
            if section == self.LABEL_COLUMN:
                return 'Label'
        if orientation == Qt.Qt.Vertical:
            return section + 1
        return None

    def data(self, index: Qt.QModelIndex, role: int = Qt.Qt.UserRole) -> Any:
        if not index.isValid():
            return None
        row = index.row()
        if row >= len(self.items):
            return None
        column = index.column()
        if column >= self.COLUMN_COUNT:
            return None

        if role in (Qt.Qt.DisplayRole,
                    Qt.Qt.   EditRole):
            if column == self.START_FRAME_COLUMN:
                return str(self.items[row].start)
            if column == self.END_FRAME_COLUMN:
                if self.items[row].end != self.items[row].start:
                    return str(self.items[row].end)
                else:
                    return ''
            if column == self.START_TIME_COLUMN:
                if not self.main.current_output.vfr:
                    return str(Time(self.items[row].start))
                else:
                    return ''
            if column == self.END_TIME_COLUMN:
                if self.items[row].end != self.items[row].start \
                   and not self.main.current_output.vfr:
                    return str(Time(self.items[row].end))
                else:
                    return ''
            if column == self.LABEL_COLUMN:
                return str(self.items[row].label)

        if role == Qt.Qt.UserRole:
            if column == self.START_FRAME_COLUMN:
                return self.items[row].start
            if column == self.END_FRAME_COLUMN:
                return self.items[row].end
            if column == self.START_TIME_COLUMN:
                if not self.main.current_output.vfr:
                    return Time(self.items[row].start)
                else:
                    return Time()
            if column == self.END_TIME_COLUMN:
                if not self.main.current_output.vfr:
                    return Time(self.items[row].end)
                else:
                    return Time()
            if column == self.LABEL_COLUMN:
                return self.items[row].label

        return None

    def setData(self, index: Qt.QModelIndex, value: Any, role: int = Qt.Qt.EditRole) -> bool:
        from copy import deepcopy

        if not index.isValid():
            return False
        if role not in (Qt.Qt.EditRole,
                        Qt.Qt.UserRole):
            return False

        row    = index.row()
        column = index.column()
        scene  = deepcopy(self.items[row])

        if column == self.START_FRAME_COLUMN:
            if not isinstance(value, Frame):
                raise TypeError
            if scene.start != scene.end:
                if value > scene.end:
                    return False
                scene.start = value
            else:
                scene.start = value
                scene.end   = value
            proper_update = True
        elif column == self.END_FRAME_COLUMN:
            if not isinstance(value, Frame):
                raise TypeError
            if scene.start != scene.end:
                if value < scene.start:
                    return False
                scene.end = value
            else:
                scene.start = value
                scene.end   = value
            proper_update = True
        elif column == self.START_TIME_COLUMN:
            if self.main.current_output.vfr:
                raise RuntimeError('start time column is set while current output is VFR')
            if not isinstance(value, Time):
                raise TypeError
            frame = Frame(value)
            if scene.start != scene.end:
                if frame > scene.end:
                    return False
                scene.start = frame
            else:
                scene.start = frame
                scene.end   = frame
            proper_update = True
        elif column == self.END_TIME_COLUMN:
            if self.main.current_output.vfr:
                raise RuntimeError('end time column is set while current output is VFR')
            if not isinstance(value, Time):
                raise TypeError
            frame = Frame(value)
            if scene.start != scene.end:
                if frame < scene.start:
                    return False
                scene.end = frame
            else:
                scene.start = frame
                scene.end   = frame
            proper_update = True
        elif column == self.LABEL_COLUMN:
            if not isinstance(value, str):
                raise TypeError
            scene.label = value
            proper_update = False

        if proper_update is True:
            i = bisect_right(self.items, scene)
            if i > row:
                i -= 1
            if i != row:
                self.beginMoveRows(self.createIndex(row, 0), row, row,
                                   self.createIndex(i, 0), i)
                del self.items[row]
                self.items.insert(i, scene)
                self.endMoveRows()
            else:
                self.items[index.row()] = scene
                self.dataChanged.emit(index, index)
        else:
            self.items[index.row()] = scene
            self.dataChanged.emit(index, index)
        return True

    def flags(self, index: Qt.QModelIndex) -> Qt.Qt.ItemFlags:
        if not index.isValid():
            return Qt.Qt.NoItemFlags
        row = index.row()
        if row >= len(self.items):
            return Qt.Qt.NoItemFlags
        column = index.column()
        if column >= self.COLUMN_COUNT:
            return Qt.Qt.NoItemFlags

        if self.main.current_output.vfr \
           and column in (self.START_TIME_COLUMN, self.END_TIME_COLUMN):
            return Qt.Qt.NoItemFlags   

        return cast(Qt.Qt.ItemFlags,
                    super().flags(index) | Qt.Qt.ItemIsSelectable | Qt.Qt.ItemIsEditable)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int) -> Scene:
        return self.items[i]

    def __setitem__(self, i: int, value: Scene) -> None:
        if i >= len(self.items):
            raise IndexError

        self.items[i] = value
        self.dataChanged.emit(
            self.createIndex(i, 0),
            self.createIndex(i, self.COLUMN_COUNT - 1))

    def __contains__(self, item: Union[Scene, Frame]) -> bool:
        if isinstance(item, Scene):
            return item in self.items
        if isinstance(item, Frame):
            for scene in self.items:
                if item in (scene.start, scene.end):
                    return True
            return False
        raise TypeError

    def __getiter__(self) -> Iterator[Scene]:
        return iter(self.items)

    def add(self, start: Frame, end: Optional[Frame] = None, label: str = '') -> Scene:
        scene = Scene(start, end, label)

        if scene in self.items:
            return scene

        if scene.end > self.main.current_output.end_frame:
            raise ValueError('New Scene is out of bounds of output')

        index = bisect_right(self.items, scene)
        self.beginInsertRows(Qt.QModelIndex(), index, index)
        self.items.insert(index, scene)
        self.endInsertRows()

        return scene

    def remove(self, i: Union[int, Scene]) -> None:
        if isinstance(i, Scene):
            i = self.items.index(i)

        if i >= 0 and i < len(self.items):
            self.beginRemoveRows(Qt.QModelIndex(), i, i)
            del(self.items[i])
            self.endRemoveRows()
        else:
            raise IndexError

    def get_next_frame(self, initial: Frame) -> Optional[Frame]:
        result       = None
        result_delta = FrameInterval(int(self.main.current_output.end_frame))
        for scene in self.items:
            if FrameInterval(0) < scene.start - initial < result_delta:
                result = scene.start
                result_delta = scene.start - initial
            if FrameInterval(0) < scene.end - initial < result_delta:
                result = scene.end
                result_delta = scene.end - initial

        return result

    def get_prev_frame(self, initial: Frame) -> Optional[Frame]:
        result       = None
        result_delta = FrameInterval(int(self.main.current_output.end_frame))
        for scene in self.items:
            if FrameInterval(0) < initial - scene.start < result_delta:
                result = scene.start
                result_delta = initial - scene.start
            if FrameInterval(0) < initial - scene.end < result_delta:
                result = scene.end
                result_delta = initial - scene.end

        return result

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        def refresh_time_columns() -> None:
            self.dataChanged.emit(
                self.createIndex(0, self.START_TIME_COLUMN),
                self.createIndex(self.rowCount() - 1, self.END_TIME_COLUMN))

        if self.main.current_output.vfr \
           and (prev_index == -1 or not self.main.outputs[prev_index].vfr):
            refresh_time_columns()
        elif not self.main.current_output.vfr \
             and (prev_index == -1 or self.main.outputs[prev_index].vfr):
            refresh_time_columns()

    def __getstate__(self) -> Mapping[str, Any]:
        return {name: getattr(self, name)
                for name in self.__slots__}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            name = state['name']
            if not isinstance(name, str):
                raise TypeError(
                    '\'name\' of a SceningList is not a string. It\'s most probably corrupted.')

            items = state['items']
            if not isinstance(items, list):
                raise TypeError(
                    '\'items\' of a SceningList is not a List. It\'s most probably corrupted.')
            for item in items:
                if not isinstance(item, Scene):
                    raise TypeError(
                        'One of the items of SceningList is not a Scene. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError(
                'SceningList lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'
                .format(', '.join(self.__slots__)))

        self.__init__(name, items)  # type: ignore


class SceningLists(Qt.QAbstractListModel, QYAMLObject):
    yaml_tag = '!SceningLists'

    __slots__ = (
        'items',
    )

    def __init__(self, items: Optional[List[SceningList]] = None) -> None:
        super().__init__()
        self.main = main_window()
        self.items = items if items is not None else []

    def __getitem__(self, i: int) -> SceningList:
        return self.items[i]

    def __len__(self) -> int:
        return len(self.items)

    def __getiter__(self) -> Iterator[SceningList]:
        return iter(self.items)

    def index_of(self, item: SceningList, start_i: int = 0, end_i: int = 0) -> int:
        if end_i == 0:
            end_i = len(self.items)
        return self.items.index(item, start_i, end_i)

    def rowCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        return len(self.items)

    def data(self, index: Qt.QModelIndex, role: int = Qt.Qt.UserRole) -> Any:
        if not index.isValid():
            return None
        if index.row() >= len(self.items):
            return None

        if role in (Qt.Qt.DisplayRole,
                    Qt.Qt.EditRole):
            return self.items[index.row()].name
        if role == Qt.Qt.UserRole:
            return self.items[index.row()]
        return None

    def flags(self, index: Qt.QModelIndex) -> Qt.Qt.ItemFlags:
        if not index.isValid():
            return cast(Qt.Qt.ItemFlags, Qt.Qt.ItemIsEnabled)

        return cast(Qt.Qt.ItemFlags,
                    super().flags(index) | Qt.Qt.ItemIsEditable)

    def setData(self, index: Qt.QModelIndex, value: Any, role: int = Qt.Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        if role not in (Qt.Qt.EditRole,
                        Qt.Qt.UserRole):
            return False
        if not isinstance(value, str):
            return False

        self.items[index.row()].name = value
        self.dataChanged.emit(index, index)
        return True

    def insertRow(self, i: int, parent: Qt.QModelIndex = Qt.QModelIndex()) -> bool:
        self.add(i=i)
        return True

    def removeRow(self, i: int, parent: Qt.QModelIndex = Qt.QModelIndex()) -> bool:
        try:
            self.remove(i)
        except IndexError:
            return False

        return True

    def add(self, name: Optional[str] = None, i: Optional[int] = None) -> Tuple[SceningList, int]:
        if i is None:
            i = len(self.items)

        self.beginInsertRows(Qt.QModelIndex(), i, i)
        if name is None:
            self.items.insert(i, SceningList('List {}'
                                             .format(len(self.items) + 1)))
        else:
            self.items.insert(i, SceningList(name))
        self.endInsertRows()
        return self.items[i], i

    def add_list(self, scening_list: SceningList) -> int:
        i = len(self.items)
        self.beginInsertRows(Qt.QModelIndex(), i, i)
        self.items.insert(i, scening_list)
        self.endInsertRows()
        return i

    def remove(self, item: Union[int, SceningList]) -> None:
        i = item
        if isinstance(i, SceningList):
            i = self.items.index(i)

        if i >= 0 and i < len(self.items):
            self.beginRemoveRows(Qt.QModelIndex(), i, i)
            del(self.items[i])
            self.endRemoveRows()
        else:
            raise IndexError

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__slots__
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            items = state['items']
            if not isinstance(items, list):
                raise TypeError(
                    '\'items\' of a SceningLists is not a List. It\'s most probably corrupted.')
            for item in items:
                if not isinstance(item, SceningList):
                    raise TypeError(
                        'One of the items of a SceningLists is not a SceningList. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError(
                'SceningLists lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'
                .format(', '.join(self.__slots__)))

        self.__init__(items)  # type: ignore
