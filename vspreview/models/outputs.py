from __future__ import annotations

from   collections import OrderedDict
from   functools   import partial
import logging
from   typing      import (
    Any, cast, get_args, get_origin, Iterator, List, Mapping, Optional,
    Type, TypeVar, Union
)

from   PyQt5       import Qt
import vapoursynth as     vs
from   yaml        import YAMLObjectMetaclass

from vspreview.core  import (
    AudioOutput, Output, QYAMLObject
)
from vspreview.utils import debug, main_window


T = TypeVar('T', Output, AudioOutput)


class Outputs(Qt.QAbstractListModel, QYAMLObject):
    yaml_tag = '!Outputs'

    __slots__ = (
        'items', 'T',
    )

    supported_types = {Output: 'video', AudioOutput: 'audio'}

    def __class_getitem__(self, ty: Type[T]) -> partial[Outputs]:
        return partial(Outputs, ty)

    def __init__(self, ty: Type[T], local_storage: Optional[Mapping[str, T]] = None) -> None:
        super().__init__()
        self.T: YAMLObjectMetaclass = ty
        self.items: List[self.T] = []

        local_storage = local_storage if local_storage is not None else {}

        if main_window().ORDERED_OUTPUTS:
            outputs = OrderedDict(sorted(vs.get_outputs().items()))
        else:
            outputs = vs.get_outputs()

        for i, vs_output in outputs.items():
            if not isinstance(vs_output, self.T.vs_type):
                continue
            try:
                output = local_storage[str(i)]
                output.__init__(vs_output, i)
            except KeyError:
                output = self.T(vs_output, i)

            self.items.append(output)

    def __getitem__(self, i: int) -> T:
        return self.items[i]

    def __len__(self) -> int:
        return len(self.items)

    def index_of(self, item: T) -> int:
        return self.items.index(item)

    def __getiter__(self) -> Iterator[T]:
        return iter(self.items)

    def append(self, item: T) -> int:
        index = len(self.items)
        self.beginInsertRows(Qt.QModelIndex(), index, index)
        self.items.append(item)
        self.endInsertRows()

        return len(self.items) - 1

    def clear(self) -> None:
        self.beginRemoveRows(Qt.QModelIndex(), 0, len(self.items))
        self.items.clear()
        self.endRemoveRows()

    def data(self, index: Qt.QModelIndex, role: int = Qt.Qt.UserRole) -> Any:
        if not index.isValid():
            return None
        if index.row() >= len(self.items):
            return None

        if role == Qt.Qt.DisplayRole:
            return self.items[index.row()].name
        if role == Qt.Qt.EditRole:
            return self.items[index.row()].name
        if role == Qt.Qt.UserRole:
            return self.items[index.row()]
        return None

    def rowCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        if self.items is not None:
            return len(self.items)

    def flags(self, index: Qt.QModelIndex) -> Qt.Qt.ItemFlags:
        if not index.isValid():
            return cast(Qt.Qt.ItemFlags, Qt.Qt.ItemIsEnabled)

        return cast(Qt.Qt.ItemFlags,
                    super().flags(index) | Qt.Qt.ItemIsEditable)

    def setData(self, index: Qt.QModelIndex, value: Any, role: int = Qt.Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        if not role == Qt.Qt.EditRole:
            return False
        if not isinstance(value, str):
            return False

        self.items[index.row()].name = value
        self.dataChanged.emit(index, index, [role])
        return True

    def __getstate__(self) -> Mapping[str, Any]:
        state = dict(zip([
            str(output.index) for output in self.items],
            [   output        for output in self.items]
        ))
        state['type'] = self.supported_types[self.T]
        return state

    def __setstate__(self, state: Mapping[str, Union[Output, str]]) -> None:
        try:
            type_string = state['type']
            if not isinstance(type_string, str):
                raise TypeError(
                    'Storage loading: Outputs: value of key "type" is not a string')
            if type_string not in self.supported_types.values():
                raise ValueError(
                    'Storage loading: Outputs: unsupported type of items')
        except KeyError:
            raise KeyError('Storage loading: Outputs: key "type" is missing') from KeyError
        ty = dict(zip(self.supported_types.values(),
                        self.supported_types.keys()))[type_string]

        for key, value in state.items():
            if key == 'type':
                continue
            if not isinstance(key, str):
                raise TypeError(
                    f'Storage loading: Outputs: key {key} is not a string')
            if not isinstance(value, ty):
                raise TypeError(
                    f'Storage loading: Outputs: value of key {key} is not an Output')

        self.__init__(ty, state)  # type: ignore
