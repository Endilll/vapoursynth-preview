from __future__ import annotations

from typing import Any, Generic, Iterator, List, Optional, TypeVar, Union

from PySide2.QtCore import QAbstractListModel, QModelIndex, Qt

T = TypeVar('T')


class ListModel(QAbstractListModel, Generic[T]):  # pylint: disable=unsubscriptable-object
    __slots__ = (
        'items',
    )

    def __init__(self, init_list: Optional[List[T]] = None) -> None:
        super().__init__()
        self._items: List[T] = init_list if init_list is not None else []

    def __getitem__(self, i: int) -> T:
        return self._items[i]

    def __len__(self) -> int:
        return len(self._items)

    def index_of(self, item: T) -> int:
        return self._items.index(item)

    def __getiter__(self) -> Iterator[T]:
        return iter(self._items)

    def append(self, item: T) -> int:
        index = len(self._items)
        self.beginInsertRows(QModelIndex(), index, index)
        self._items.append(item)
        self.endInsertRows()  # type: ignore

        return len(self._items) - 1

    def clear(self) -> None:
        if len(self) == 0:
            return

        self.beginRemoveRows(QModelIndex(), 0, len(self._items) - 1)
        self._items.clear()
        self.endRemoveRows()  # type: ignore

    def data(self, index: QModelIndex, role: int = Qt.UserRole) -> Optional[Union[str, T]]:  # type: ignore
        if not index.isValid():
            return None
        if index.row() >= len(self._items):
            return None

        if role == Qt.DisplayRole:  # type: ignore
            return str(self._items[index.row()])
        if role == Qt.EditRole:  # type: ignore
            return str(self._items[index.row()])
        if role == Qt.UserRole:  # type: ignore
            return self._items[index.row()]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def flags(self, index: QModelIndex) -> int:
        if not index.isValid():
            return Qt.ItemIsEnabled  # type: ignore

        return super().flags(index) | Qt.ItemIsEditable  # type: ignore

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:  # type: ignore
        if not index.isValid():
            return False
        if not role == Qt.EditRole:  # type: ignore
            return False

        self._items[index.row()] = value
        self.dataChanged.emit(index, index, [role])
        return True
