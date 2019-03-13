from __future__ import annotations

import logging
from   typing  import Any, cast, List, Mapping, Optional

from   PyQt5       import Qt
import vapoursynth as     vs

from vspreview.core  import Output, QYAMLObject
from vspreview.utils import debug

# TODO: enable editing output name in combobox
# TODO: consider converting it to singleton


class Outputs(Qt.QAbstractListModel, QYAMLObject):
    __slots__ = (
        'items'
    )

    yaml_tag = '!Outputs'

    def __init__(self, local_storage: Optional[Mapping[str, Output]] = None) -> None:
        super().__init__()
        self.items: List[Output] = []

        local_storage = local_storage if local_storage is not None else {}
        for i, vs_output in vs.get_outputs().items():
            pixel_format = vs_output.format
            vs_output    = vs.core.resize.Bicubic(vs_output, format=vs.COMPATBGR32, matrix_in_s='709', chromaloc=0, prefer_props=1)
            vs_output    = vs.core.std.FlipVertical(vs_output)

            try:
                output = local_storage[str(i)]
                output.__init__(vs_output, i, pixel_format)  # type: ignore
            except KeyError:
                output = Output(vs_output, i, pixel_format)

            self.items.append(output)

    def __getitem__(self, i: int) -> Output:
        return self.items[i]

    def __len__(self) -> int:
        return len(self.items)

    def append(self, item: Output) -> int:
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
        # debug.print_func_name()
        if not index.isValid():
            return None
        if index.row() >= len(self.items):
            return None

        if   role == Qt.Qt.DisplayRole:
            return self.items[index.row()].name
        if   role == Qt.Qt.EditRole:
            return self.items[index.row()].name
        elif role == Qt.Qt.UserRole:
            # logging.debug('UserRole')
            return self.items[index.row()]
        else:
            return None

    def rowCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        # debug.print_func_name()
        if self.items is not None:
            return len(self.items)
        else:
            return 0

    def flags(self, index: Qt.QModelIndex) -> Qt.Qt.ItemFlags:
        # debug.print_func_name()
        if not index.isValid():
            return cast(Qt.Qt.ItemFlags, Qt.Qt.ItemIsEnabled)

        return cast(Qt.Qt.ItemFlags, super().flags(index) | Qt.Qt.ItemIsEditable)

    def setData(self, index: Qt.QModelIndex, value: Any, role: int = Qt.Qt.EditRole) -> bool:
        # debug.print_func_name()
        # logging.debug(index.row())
        # logging.debug(value)
        if not index.isValid():
            return False
        if not isinstance(value, str):
            return False
        if not role == Qt.Qt.EditRole:
            return False

        self.items[index.row()].name = value
        self.dataChanged.emit(index, index, [role])
        return True

    def itemText(self, i: int) -> str:
        debug.print_func_name()
        return 'itemText'

    def setItemData(self, index: Qt.QModelIndex, roles: Any) -> bool:
        debug.print_func_name()
        return True

    def insertRows(self, pos: int, count: int, index: Optional[Qt.QModelIndex] = None) -> bool:
        debug.print_func_name()
        logging.debug(pos)
        return True

    def __getstate__(self) -> Mapping[str, Any]:
        # print(self.items)
        return dict(zip([
            str(output.index) for output in self.items],
            [   output        for output in self.items]
        ))

    def __setstate__(self, state: Mapping[str, Output]) -> None:
        self.__init__(state)  # type: ignore


class ItemEditDelegate(Qt.QStyledItemDelegate):
    def __init__(self, parent: Optional[Qt.QWidget] = None) -> None:
        super().__init__(parent)
        self.a = 1

    def setModelData(self, editor: Qt.QWidget, model: Qt.QAbstractItemModel, index: Qt.QModelIndex) -> None:
        debug.print_func_name()

    def createEditor(self, parent: Qt.QWidget, option: Qt.QStyleOptionViewItem, index: Qt.QModelIndex) -> Qt.QWidget:
        debug.print_func_name()

        return Qt.QLineEdit()

    def setEditorData(self, editor: Qt.QWidget, index: Qt.QModelIndex) -> None:
        debug.print_func_name()
