from __future__ import annotations

from   bisect   import bisect_left, bisect_right
from   datetime import timedelta
import logging
from   pathlib  import Path
import re
from   typing   import Any, Callable, cast, Dict, Iterator, List, Mapping, Optional, Set, Tuple, Union

from PyQt5 import Qt

from vspreview.core    import AbstractMainWindow, AbstractToolbar, Frame, FrameInterval, QYAMLObject, Scene
from vspreview.utils   import (add_shortcut, debug, main_window, fire_and_forget, qtime_to_timedelta,
                               qt_silent_call, set_qobject_names, set_status_label, strfdelta, timedelta_to_qtime)
from vspreview.widgets import ComboBox, Notches


class SceningList(Qt.QAbstractTableModel, QYAMLObject):
    __slots__ = (
        'name', 'items', 'max_value'
    )
    yaml_tag = '!SceningList'

    START_FRAME_COLUMN = 0
    END_FRAME_COLUMN   = 1
    START_TIME_COLUMN  = 2
    END_TIME_COLUMN    = 3
    LABEL_COLUMN       = 4
    COLUMN_COUNT       = 5

    def __init__(self, name: str = '', max_value: Optional[Frame] = None, items: Optional[List[Scene]] = None) -> None:
        super().__init__()
        self.name      = name
        self.max_value = max_value if max_value is not None else Frame(2**31)
        self.items     =     items if     items is not None else []

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
                return strfdelta(main_window().to_timedelta(self.items[row].start), '%h:%M:%S.%Z')
            if column == self.END_TIME_COLUMN:
                if self.items[row].end != self.items[row].start:
                    return strfdelta(main_window().to_timedelta(self.items[row].end), '%h:%M:%S.%Z')
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
                return main_window().to_timedelta(self.items[row].start)
            if column == self.END_TIME_COLUMN:
                return main_window().to_timedelta(self.items[row].end)
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
            if value > scene.end:
                return False
            scene.start = value
            proper_update = True
        elif column == self.END_FRAME_COLUMN:
            if not isinstance(value, Frame):
                raise TypeError
            if value < scene.start:
                return False
            scene.end = value
            proper_update = True
        if column == self.START_TIME_COLUMN:
            if not isinstance(value, timedelta):
                raise TypeError
            frame = self.main.to_frame(value)
            if frame > scene.end:
                return False
            scene.start = frame
            proper_update = True
        if column == self.END_TIME_COLUMN:
            if not isinstance(value, timedelta):
                raise TypeError
            frame = self.main.to_frame(value)
            if frame < scene.start:
                return False
            scene.end = frame
            proper_update = True
        elif column == self.LABEL_COLUMN:
            if not isinstance(value, str):
                raise TypeError
            scene.label = value
            proper_update = False

        if proper_update is True:
            i = bisect_right(self.items, scene)
            if i >= row:
                i -= 1
            if i != row:
                self.beginMoveRows(self.createIndex(row, 0), row, row, self.createIndex(i, 0), i)
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
            self.createIndex(i, self.COLUMN_COUNT - 1)
        )

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

        if scene.end > self.max_value:
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
        result_delta = FrameInterval(int(self.max_value))
        for scene in self.items:
            if 0 < scene.start - initial < result_delta:
                result = scene.start
                result_delta = scene.start - initial
            if 0 < scene.end - initial < result_delta:
                result = scene.end
                result_delta = scene.end - initial

        return result

    def get_prev_frame(self, initial: Frame) -> Optional[Frame]:
        result       = None
        result_delta = FrameInterval(int(self.max_value))
        for scene in self.items:
            if 0 < initial - scene.start < result_delta:
                result = scene.start
                result_delta = scene.start - initial
            if 0 < initial - scene.end < result_delta:
                result = scene.end
                result_delta = scene.end - initial

        return result

    def __getstate__(self) -> Mapping[str, Any]:
        return {name: getattr(self, name)
                for name in self.__slots__}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            max_value = state['max_value']
            if not isinstance(max_value, Frame):
                raise TypeError('\'max_value\' of a SceningList is not a Frame. It\'s most probably corrupted.')

            name = state['name']
            if not isinstance(name, str):
                raise TypeError('\'name\' of a SceningList is not a Frame. It\'s most probably corrupted.')

            items = state['items']
            if not isinstance(items, list):
                raise TypeError('\'items\' of a SceningList is not a List. It\'s most probably corrupted.')
            for item in items:
                if not isinstance(item, Scene):
                    raise TypeError('One of the items of SceningList is not a Scene. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('SceningList lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(name, max_value, items)  # type: ignore


class SceningLists(Qt.QAbstractListModel, QYAMLObject):
    __slots__ = (
        'items',
    )
    yaml_tag = '!SceningLists'

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

        return cast(Qt.Qt.ItemFlags, super().flags(index) | Qt.Qt.ItemIsEditable)

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

    def add(self, name: Optional[str] = None, max_value: Optional[Frame] = None, i: Optional[int] = None) -> Tuple[SceningList, int]:
        if max_value is None:
            max_value = self.main.current_output.total_frames - FrameInterval(1)
        if i is None:
            i = len(self.items)

        self.beginInsertRows(Qt.QModelIndex(), i, i)
        if name is None:
            self.items.insert(i, SceningList('List {}'.format(len(self.items) + 1), max_value))
        else:
            self.items.insert(i, SceningList(name, max_value))
        self.endInsertRows()
        return self.items[i], i

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
                raise TypeError('\'items\' of a SceningLists is not a List. It\'s most probably corrupted.')
            for item in items:
                if not isinstance(item, SceningList):
                    raise TypeError('One of the items of a SceningLists is not a SceningList. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('SceningLists lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(items)  # type: ignore


class SceningListDialog(Qt.QDialog):
    __slots__ = (
        'main', 'scening_list',
        'name_lineedit', 'tableview',
        'start_frame_lineedit', 'end_frame_lineedit',
        'label_lineedit',
    )

    def __init__(self, main: AbstractMainWindow) -> None:
        super().__init__(main)

        self.main = main
        self.scening_list = SceningList()

        self.setWindowTitle('Scening List View')
        self.setup_ui()

        self.end_frame_lineedit  .textChanged.connect(self.on_end_frame_changed)
        self.end_time_spinbox    .timeChanged.connect(lambda qtime: self.on_end_time_changed(qtime_to_timedelta(qtime)))  # type: ignore
        self.label_lineedit      .textChanged.connect(self.on_label_changed)
        self.name_lineedit       .textChanged.connect(self.on_name_changed)
        self.start_frame_lineedit.textChanged.connect(self.on_start_frame_changed)
        self.start_time_spinbox  .timeChanged.connect(lambda qtime: self.on_start_time_changed(qtime_to_timedelta(qtime)))  # type: ignore
        self.tableview         .doubleClicked.connect(self.on_tableview_clicked)

        set_qobject_names(self)

    def setup_ui(self) -> None:
        layout = Qt.QVBoxLayout(self)
        layout.setObjectName('SceningListDialog.setup_ui.layout')

        self.name_lineedit = Qt.QLineEdit(self)
        layout.addWidget(self.name_lineedit)

        self.tableview = Qt.QTableView(self)
        self.tableview.setSelectionMode(Qt.QTableView.SingleSelection)
        self.tableview.setSelectionBehavior(Qt.QTableView.SelectRows)
        self.tableview.setSizeAdjustPolicy(Qt.QTableView.AdjustToContents)
        layout.addWidget(self.tableview)

        scene_layout = Qt.QHBoxLayout()
        scene_layout.setObjectName('SceningListDialog.setup_ui.scene_layout')
        layout.addLayout(scene_layout)

        self.start_frame_lineedit = Qt.QLineEdit(self)
        self.start_frame_lineedit.setPlaceholderText('Start Frame')
        self.start_frame_lineedit.setValidator(Qt.QRegExpValidator(Qt.QRegExp(r'\d+')))
        scene_layout.addWidget(self.start_frame_lineedit)

        self.end_frame_lineedit = Qt.QLineEdit(self)
        self.end_frame_lineedit.setPlaceholderText('End Frame')
        self.end_frame_lineedit.setValidator(Qt.QRegExpValidator(Qt.QRegExp(r'\d+')))
        scene_layout.addWidget(self.end_frame_lineedit)

        self.start_time_spinbox = Qt.QTimeEdit(self)
        self.start_time_spinbox.setMinimumTime(Qt.QTime())
        self.start_time_spinbox.setDisplayFormat('H:mm:ss.zzz')
        self.start_time_spinbox.setButtonSymbols(Qt.QTimeEdit.NoButtons)
        scene_layout.addWidget(self.start_time_spinbox)

        self.end_time_spinbox = Qt.QTimeEdit(self)
        self.end_time_spinbox.setMinimumTime(Qt.QTime())
        self.end_time_spinbox.setDisplayFormat('H:mm:ss.zzz')
        self.end_time_spinbox.setButtonSymbols(Qt.QTimeEdit.NoButtons)
        scene_layout.addWidget(self.end_time_spinbox)

        self.label_lineedit = Qt.QLineEdit(self)
        self.label_lineedit.setPlaceholderText('Label')
        scene_layout.addWidget(self.label_lineedit)

        # self.add_button = Qt.QPushButton(self)
        # self.add_button.setText('Add')
        # self.add_button.setEnabled(False)
        # scene_layout.addWidget(self.add_button)

    def on_add_clicked(self, checked: Optional[bool] = None) -> None:
        pass

    def on_current_frame_changed(self, frame: Frame, t: timedelta) -> None:
        if not self.isVisible():
            return
        if self.tableview.selectionModel() is None:
            return
        selection = Qt.QItemSelection()
        for i, scene in enumerate(self.scening_list):
            if frame in scene:
                index = self.scening_list.index(i, 0)
                selection.select(index, index)
        self.tableview.selectionModel().select(
            selection,
            Qt.QItemSelectionModel.SelectionFlags(  # type: ignore
                Qt.QItemSelectionModel.Rows + Qt.QItemSelectionModel.ClearAndSelect))

    def on_current_list_changed(self, scening_list: Optional[SceningList] = None) -> None:
        if scening_list is not None:
            self.scening_list = scening_list
        else:
            self.scening_list = self.main.toolbars.scening.current_list

        self.scening_list.rowsMoved.connect(self.on_tableview_rows_moved)  # type: ignore

        self.name_lineedit.setText(self.scening_list.name)

        self.tableview.setModel(self.scening_list)
        self.tableview.resizeColumnsToContents()
        self.tableview.selectionModel().selectionChanged.connect(self.on_tableview_selection_changed)  # type: ignore

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        self.start_time_spinbox.setMaximumTime(timedelta_to_qtime(self.main.to_timedelta(self.main.current_output.total_frames)))
        self.  end_time_spinbox.setMaximumTime(timedelta_to_qtime(self.main.to_timedelta(self.main.current_output.total_frames)))

    def on_end_frame_changed(self, text: str) -> None:
        try:
            frame = Frame(int(self.end_frame_lineedit.text()))
        except ValueError:
            return
        index = self.tableview.selectionModel().selectedRows()[0]
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.END_FRAME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, frame, Qt.Qt.UserRole)

    def on_end_time_changed(self, t: timedelta) -> None:
        index = self.tableview.selectionModel().selectedRows()[0]
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.END_TIME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, t, Qt.Qt.UserRole)

    def on_label_changed(self, text: str) -> None:
        index = self.tableview.selectionModel().selectedRows()[0]
        if not index.isValid():
            return
        index = self.scening_list.index(index.row(), SceningList.LABEL_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, text, Qt.Qt.UserRole)

    def on_name_changed(self, text: str) -> None:
        i = self.main.current_output.scening_lists.index_of(self.scening_list)
        index = self.main.current_output.scening_lists.index(i)
        self.main.current_output.scening_lists.setData(index, text, Qt.Qt.UserRole)

    def on_start_frame_changed(self, text: str) -> None:
        try:
            frame = Frame(int(self.start_frame_lineedit.text()))
        except ValueError:
            return
        index = self.tableview.selectionModel().selectedRows()[0]
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.START_FRAME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, frame, Qt.Qt.UserRole)

    def on_start_time_changed(self, t: timedelta) -> None:
        index = self.tableview.selectionModel().selectedRows()[0]
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.START_TIME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, t, Qt.Qt.UserRole)

    def on_tableview_clicked(self, index: Qt.QModelIndex) -> None:
        if index.column() in (SceningList.START_FRAME_COLUMN,
                              SceningList.END_FRAME_COLUMN):
            self.main.current_frame = self.scening_list.data(index)
        if index.column() == SceningList.START_TIME_COLUMN:
            self.main.current_frame = self.scening_list.data(index.siblingAtColumn(SceningList.START_FRAME_COLUMN))
        if index.column() == SceningList.END_TIME_COLUMN:
            self.main.current_frame = self.scening_list.data(index.siblingAtColumn(SceningList.END_FRAME_COLUMN))

    def on_tableview_rows_moved(self, parent_index: Qt.QModelIndex, start_i: int, end_i: int, dest_index: Qt.QModelIndex, dest_i: int) -> None:
        index = self.scening_list.index(dest_i, 0)
        self.tableview.selectionModel().select(
            index,
            Qt.QItemSelectionModel.SelectionFlags(  # type: ignore
                Qt.QItemSelectionModel.Rows + Qt.QItemSelectionModel.ClearAndSelect))

    def on_tableview_selection_changed(self, selected: Qt.QItemSelection, deselected: Qt.QItemSelection) -> None:
        if len(selected.indexes()) == 0:
            return
        index = selected.indexes()[0]
        scene = self.scening_list[index.row()]
        qt_silent_call(self.start_frame_lineedit.setText, str(scene.start))
        qt_silent_call(self.  end_frame_lineedit.setText, str(scene.end))
        qt_silent_call(self.  start_time_spinbox.setTime, timedelta_to_qtime(self.main.to_timedelta(scene.start)))
        qt_silent_call(self.    end_time_spinbox.setTime, timedelta_to_qtime(self.main.to_timedelta(scene.end)))
        qt_silent_call(self.      label_lineedit.setText,     scene.label)


class SceningToolbar(AbstractToolbar):
    __slots__ = (
        'first_frame', 'second_frame',
        'export_template_pattern', 'export_template_scenes_pattern',
        'scening_list_dialog', 'supported_file_types',
        'add_list_button', 'remove_list_button', 'view_list_button',
        'toggle_first_frame_button', 'toggle_second_frame_button', 'add_single_frame_button',
        'add_to_list_button', 'remove_last_from_list_button',
        'export_single_line_button', 'export_template_lineedit', 'export_multiline_button',
        'status_label', 'import_file_button', 'items_combobox', 'remove_at_current_frame_button',
        'seek_to_next_button', 'seek_to_prev_button',
        'toggle_button'
    )

    def __init__(self, main: AbstractMainWindow) -> None:
        super().__init__(main)
        self.setup_ui()

        self.first_frame : Optional[Frame] = None
        self.second_frame: Optional[Frame] = None
        self.export_template_pattern  = re.compile(r'.*(?:{start}|{end}|{label}).*')
        self.export_template_scenes_pattern = re.compile(r'.+')

        self.scening_update_status_label()
        self.scening_list_dialog = SceningListDialog(self.main)

        self.supported_file_types = {
            'Aegisub Project (*.ass)'       : self.import_ass,
            'CUE Sheet (*.cue)'             : self.import_cue,
            'DGIndex Project (*.dgi)'       : self.import_dgi,
            'Matroska Timestamps v1 (*.txt)': self.import_matroska_timestamps_v1,
            'Matroska Timestamps v2 (*.txt)': self.import_matroska_timestamps_v2,
            'Matroska XML Chapters (*.xml)' : self.import_matroska_xml_chapters,
            'OGM Chapters (*.txt)'          : self.import_ogm_chapters,
            'TFM Log (*.txt)'               : self.import_tfm,
            'x264/x265 QP File (*.qp)'      : self.import_qp,
            'XviD Log (*.txt)'              : self.import_xvid,
        }

        self.toggle_button                 .clicked.connect(self.on_toggle)
        self.add_list_button               .clicked.connect(self.on_add_list_clicked)
        self.add_single_frame_button       .clicked.connect(self.on_add_single_frame_clicked)
        self.add_to_list_button            .clicked.connect(self.on_add_to_list_clicked)
        self.export_multiline_button       .clicked.connect(self.export_multiline)
        self.export_single_line_button     .clicked.connect(self.export_single_line)
        self.export_template_lineedit  .textChanged.connect(self.check_remove_export_possibility)
        self.import_file_button            .clicked.connect(self.on_import_file_clicked)
        self.items_combobox           .indexChanged.connect(self.on_current_list_changed)
        self.remove_at_current_frame_button.clicked.connect(self.on_remove_at_current_frame_clicked)
        self.remove_last_from_list_button  .clicked.connect(self.on_remove_last_from_list_clicked)
        self.remove_list_button            .clicked.connect(self.on_remove_list_clicked)
        self.seek_to_next_button           .clicked.connect(self.on_seek_to_next_clicked)
        self.seek_to_prev_button           .clicked.connect(self.on_seek_to_prev_clicked)
        self.toggle_first_frame_button     .clicked.connect(self.on_first_frame_clicked)
        self.toggle_second_frame_button    .clicked.connect(self.on_second_frame_clicked)
        self.view_list_button              .clicked.connect(self.on_view_list_clicked)

        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_1, lambda: self.switch_list(0))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_2, lambda: self.switch_list(1))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_3, lambda: self.switch_list(2))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_4, lambda: self.switch_list(3))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_5, lambda: self.switch_list(4))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_6, lambda: self.switch_list(5))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_7, lambda: self.switch_list(6))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_8, lambda: self.switch_list(7))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_9, lambda: self.switch_list(8))

        add_shortcut(Qt.Qt.CTRL  + Qt.Qt.Key_Space, self.on_toggle_single_frame)
        add_shortcut(Qt.Qt.CTRL  + Qt.Qt.Key_Left,  self.seek_to_next_button         .click)
        add_shortcut(Qt.Qt.CTRL  + Qt.Qt.Key_Right, self.seek_to_prev_button         .click)
        add_shortcut(              Qt.Qt.Key_Q,     self.toggle_first_frame_button   .click)
        add_shortcut(              Qt.Qt.Key_W,     self.toggle_second_frame_button  .click)
        add_shortcut(              Qt.Qt.Key_E,     self.add_to_list_button          .click)
        add_shortcut(              Qt.Qt.Key_R,     self.remove_last_from_list_button.click)

        # FIXME: get rid of workaround
        self._on_list_items_changed = lambda *arg: self.on_list_items_changed(*arg)  # pylint: disable=unnecessary-lambda, no-value-for-parameter

        set_qobject_names(self)

    def setup_ui(self) -> None:
        self.setVisible(False)

        layout = Qt.QVBoxLayout(self)
        layout.setObjectName('SceningToolbar.setup_ui.layout')
        layout.setContentsMargins(0, 0, 0, 0)

        layout_line_1 = Qt.QHBoxLayout()
        layout_line_1.setObjectName('SceningToolbar.setup_ui.layout_line_1')
        layout.addLayout(layout_line_1)

        self.items_combobox = ComboBox(self)
        # self.items_combobox.setEditable(True)
        # self.items_combobox.setInsertPolicy(Qt.QComboBox.InsertAtCurrent)
        self.items_combobox.setDuplicatesEnabled(True)
        self.items_combobox.setMinimumContentsLength(4)
        layout_line_1.addWidget(self.items_combobox)

        self.add_list_button = Qt.QPushButton(self)
        self.add_list_button.setText('Add List')
        layout_line_1.addWidget(self.add_list_button)

        self.remove_list_button = Qt.QPushButton(self)
        self.remove_list_button.setText('Remove List')
        self.remove_list_button.setEnabled(False)
        layout_line_1.addWidget(self.remove_list_button)

        self.view_list_button = Qt.QPushButton(self)
        self.view_list_button.setText('View List')
        self.view_list_button.setEnabled(False)
        layout_line_1.addWidget(self.view_list_button)

        self.import_file_button = Qt.QPushButton(self)
        self.import_file_button.setText('Import List')
        layout_line_1.addWidget(self.import_file_button)

        separator = Qt.QFrame(self)
        separator.setFrameShape(Qt.QFrame.VLine)
        separator.setFrameShadow(Qt.QFrame.Sunken)
        layout_line_1.addWidget(separator)

        self.seek_to_prev_button = Qt.QPushButton(self)
        self.seek_to_prev_button.setText('⏪')
        self.seek_to_prev_button.setEnabled(False)
        layout_line_1.addWidget(self.seek_to_prev_button)

        self.seek_to_next_button = Qt.QPushButton(self)
        self.seek_to_next_button.setText('⏩')
        self.seek_to_next_button.setEnabled(False)
        layout_line_1.addWidget(self.seek_to_next_button)

        layout_line_1.addStretch()


        layout_line_2 = Qt.QHBoxLayout()
        layout_line_2.setObjectName('SceningToolbar.setup_ui.layout_line_2')
        layout.addLayout(layout_line_2)

        self.add_single_frame_button = Qt.QPushButton(self)
        self.add_single_frame_button.setText('Add Single Frame')
        layout_line_2.addWidget(self.add_single_frame_button)

        self.toggle_first_frame_button = Qt.QPushButton(self)
        self.toggle_first_frame_button.setText('Frame 1')
        self.toggle_first_frame_button.setCheckable(True)
        layout_line_2.addWidget(self.toggle_first_frame_button)

        self.toggle_second_frame_button = Qt.QPushButton(self)
        self.toggle_second_frame_button.setText('Frame 2')
        self.toggle_second_frame_button.setCheckable(True)
        layout_line_2.addWidget(self.toggle_second_frame_button)

        self.label_lineedit = Qt.QLineEdit(self)
        self.label_lineedit.setPlaceholderText('New Scene Label')
        layout_line_2.addWidget(self.label_lineedit)

        self.add_to_list_button = Qt.QPushButton(self)
        self.add_to_list_button.setText('Add to List')
        self.add_to_list_button.setEnabled(False)
        layout_line_2.addWidget(self.add_to_list_button)

        self.remove_last_from_list_button = Qt.QPushButton(self)
        self.remove_last_from_list_button.setText('Remove Last')
        self.remove_last_from_list_button.setEnabled(False)
        layout_line_2.addWidget(self.remove_last_from_list_button)

        self.remove_at_current_frame_button = Qt.QPushButton(self)
        self.remove_at_current_frame_button.setText('Remove at Current Frame')
        self.remove_at_current_frame_button.setEnabled(False)
        layout_line_2.addWidget(self.remove_at_current_frame_button)

        separator = Qt.QFrame(self)
        separator.setObjectName('SceningToolbar.setup_ui.separator')
        separator.setFrameShape(Qt.QFrame.VLine)
        separator.setFrameShadow(Qt.QFrame.Sunken)
        layout_line_2.addWidget(separator)

        self.export_template_lineedit = Qt.QLineEdit(self)
        # self.export_template_scene_lineedit.setSizePolicy(Qt.QSizePolicy(Qt.QSizePolicy.Policy.Expanding, Qt.QSizePolicy.Policy.Fixed))
        self.export_template_lineedit.setToolTip(r'Use {start} and {end} as placeholders. Both are valid for single frame scenes. {label} is available, too.')
        self.export_template_lineedit.setPlaceholderText('Export Template')
        layout_line_2.addWidget(self.export_template_lineedit)

        self.export_multiline_button = Qt.QPushButton(self)
        self.export_multiline_button.setText('Export Multiline')
        self.export_multiline_button.setEnabled(False)
        layout_line_2.addWidget(self.export_multiline_button)

        self.export_single_line_button = Qt.QPushButton(self)
        self.export_single_line_button.setText('Export Single Line')
        self.export_single_line_button.setEnabled(False)
        layout_line_2.addWidget(self.export_single_line_button)

        layout_line_2.addStretch()
        layout_line_2.addStretch()

        # statusbar label

        self.status_label = Qt.QLabel(self)
        self.status_label.setVisible(False)
        self.main.statusbar.addPermanentWidget(self.status_label)

        # switch button for main layout

        self.toggle_button.setText('Scening')

    def on_toggle(self, new_state: bool) -> None:
        # if new_state is True:
        #     self.check_add_to_list_possibility()
        #     self.check_remove_export_possibility()

        self.status_label.setVisible(new_state)
        super().on_toggle(new_state)

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        if prev_index != -1:
            for scening_list in self.main.outputs[prev_index].scening_lists:
                try:
                    scening_list.rowsInserted.disconnect(self.on_list_items_changed)
                    scening_list.rowsRemoved .disconnect(self.on_list_items_changed)
                except TypeError:
                    pass

        self.items_combobox.setModel(self.current_lists)
        self.notches_changed.emit(self)
        self.scening_list_dialog.on_current_output_changed(index, prev_index)

    def on_current_frame_changed(self, frame: Frame, t: timedelta) -> None:
        self.check_remove_export_possibility()
        self.scening_list_dialog.on_current_frame_changed(frame, t)

    def get_notches(self) -> Notches:
        marks = Notches()
        if self.current_list is None:
            return marks
        for scene in self.current_list:
            marks.add(scene, cast(Qt.QColor, Qt.Qt.green))
        return marks

    @property
    def current_list(self) -> Optional[SceningList]:
        return cast(Optional[SceningList], self.items_combobox.currentData())

    @current_list.setter
    def current_list(self, item: SceningList) -> None:
        i = self.current_lists.index(item)
        self.current_list_index = i

    @property
    def current_lists(self) -> SceningLists:
        return self.main.current_output.scening_lists

    @property
    def current_list_index(self) -> int:
        return self.items_combobox.currentIndex()

    @current_list_index.setter
    def current_list_index(self, index: int) -> None:
        if not (0 <= index < len(self.current_lists)):
            raise IndexError
        self.items_combobox.setCurrentIndex(index)

    # list management

    def on_add_list_clicked(self, checked: Optional[bool] = None) -> None:
        _, i = self.current_lists.add()
        self.current_list_index = i

    def on_current_list_changed(self, new_index: int, old_index: int) -> None:
        if new_index == -1:
            self.remove_list_button.setEnabled(False)
            self.  view_list_button.setEnabled(False)
        else:
            self.remove_list_button.setEnabled(True)
            self.  view_list_button.setEnabled(True)
            self.current_list.rowsInserted.connect(self._on_list_items_changed)  # type: ignore
            self.current_list.rowsRemoved .connect(self._on_list_items_changed)  # type: ignore
            self.scening_list_dialog.on_current_list_changed(self.current_list)

        if old_index != -1:
            try:
                self.current_lists[old_index].rowsInserted.disconnect(self._on_list_items_changed)  # type: ignore
                self.current_lists[old_index].rowsRemoved .disconnect(self._on_list_items_changed)  # type: ignore
            except (IndexError, TypeError):
                pass

        self.check_add_to_list_possibility()
        self.check_remove_export_possibility()
        self.notches_changed.emit(self)

    def on_list_items_changed(self, parent: Qt.QModelIndex, first: int, last: int) -> None:
        self.notches_changed.emit(self)

    def on_remove_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.current_lists.remove(self.current_list_index)

    def on_view_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.scening_list_dialog.show()

    def switch_list(self, index: int) -> None:
        try:
            self.current_list_index = index
        except IndexError:
            pass

    # seeking

    def on_seek_to_next_clicked(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            return

        new_pos = self.current_list.get_next_frame(self.main.current_frame)
        if new_pos is None:
            return
        self.main.current_frame = new_pos

    def on_seek_to_prev_clicked(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            return

        new_pos = self.current_list.get_prev_frame(self.main.current_frame)
        if new_pos is None:
            return
        self.main.current_frame = new_pos

    # scene management

    def on_add_single_frame_clicked(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            self.on_add_list_clicked()
        cast(SceningList, self.current_list).add(self.main.current_frame)
        self.check_remove_export_possibility()

    def on_add_to_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.current_list.add(self.first_frame, self.second_frame, self.label_lineedit.text())  # type: ignore

        if self.toggle_first_frame_button.isChecked():
            self.toggle_first_frame_button.click()
        if self.toggle_second_frame_button.isChecked():
            self.toggle_second_frame_button.click()
        self.add_to_list_button.setEnabled(False)
        self.label_lineedit.setText('')

        self.check_remove_export_possibility()

    def on_first_frame_clicked(self, checked: bool, frame: Optional[Frame] = None) -> None:
        if frame is None:
            frame = self.main.current_frame

        if checked:
            self.first_frame = frame
        else:
            self.first_frame = None
        self.scening_update_status_label()
        self.check_add_to_list_possibility()

    def on_remove_at_current_frame_clicked(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            return

        for scene in self.current_list:
            if (scene.start == self.main.current_frame
                    or scene.end == self.main.current_frame):
                self.current_list.remove(scene)

        self.remove_at_current_frame_button.clearFocus()
        self.check_remove_export_possibility()

    def on_remove_last_from_list_clicked(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            return

        self.current_list.remove(self.current_list[-1])
        self.remove_last_from_list_button.clearFocus()
        self.check_remove_export_possibility()

    def on_second_frame_clicked(self, checked: bool, frame: Optional[Frame] = None) -> None:
        if frame is None:
            frame = self.main.current_frame

        if checked:
            self.second_frame = frame
        else:
            self.second_frame = None
        self.scening_update_status_label()
        self.check_add_to_list_possibility()

    def on_toggle_single_frame(self) -> None:
        if self.add_single_frame_button.isEnabled():
            self.add_single_frame_button.click()
        elif self.remove_at_current_frame_button.isEnabled():
            self.remove_at_current_frame_button.click()

    # import

    def on_import_file_clicked(self, checked: Optional[bool] = None) -> None:
        filter_str = ';;'.join(self.supported_file_types.keys())
        path_strs, file_type = Qt.QFileDialog.getOpenFileNames(self.main, caption='Open chapters file', filter=filter_str)

        paths = [Path(path_str) for path_str in path_strs]
        for path in paths:
            self.import_file(self.supported_file_types[file_type], path)

    @fire_and_forget
    @set_status_label('Importing scenes')
    def import_file(self, import_func: Callable[[Path, SceningList, int], None], path: Path) -> None:
        out_of_range_count = 0
        scening_list, scening_list_index = self.current_lists.add(path.stem)

        import_func(path, scening_list, out_of_range_count)

        if out_of_range_count > 0:
            logging.warning(f'Scening import: {out_of_range_count} scenes were out of range of output, so they were dropped.')
        if len(scening_list) == 0:
            logging.warning(f'Scening import: nothing was imported from \'{path.name}\'.')
            self.current_lists.remove(scening_list_index)
        else:
            self.current_list_index = scening_list_index

    def import_ass(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        import pysubs2

        subs = pysubs2.load(str(path))
        for line in subs:
            t_start = timedelta(milliseconds=line.start)
            t_end   = timedelta(milliseconds=line.end)
            try:
                scening_list.add(self.main.to_frame(t_start), self.main.to_frame(t_end))
            except ValueError:
                out_of_range_count += 1

    def import_cue(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        from cueparser import CueSheet

        def offset_to_timedelta(offset: str) -> Optional[timedelta]:
            pattern = re.compile(r'(\d{1,2}):(\d{1,2}):(\d{1,2})')
            match = pattern.match(offset)
            if match is None:
                return None
            return timedelta(
                minutes = int(match[1]),
                seconds = int(match[2]),
                milliseconds = int(match[3]) / 75 * 1000
            )

        cue_sheet = CueSheet()
        cue_sheet.setOutputFormat('')
        cue_sheet.setData(path.read_text())
        cue_sheet.parse()

        for track in cue_sheet.tracks:
            if track.offset is None:
                continue
            offset = offset_to_timedelta(track.offset)
            if offset is None:
                logging.warning(f'Scening import: INDEX timestamp \'{track.offset}\' format isn\'t suported.')
                continue
            start = self.main.to_frame(offset)

            end = None
            if track.duration is not None:
                end = self.main.to_frame(offset + track.duration)

            label = ''
            if track.title is not None:
                label = track.title

            try:
                scening_list.add(start, end, label)
            except ValueError:
                out_of_range_count += 1

    def import_dgi(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        pattern = re.compile(r'IDR\s\d+\n(\d+):FRM', re.RegexFlag.MULTILINE)
        for match in pattern.findall(path.read_text()):
            try:
                scening_list.add(Frame(match))
            except ValueError:
                out_of_range_count += 1

    def import_matroska_xml_chapters(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        from xml.etree import ElementTree

        timestamp_pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2}(?:\.\d{3})?)')

        try:
            root = ElementTree.parse(str(path)).getroot()
        except ElementTree.ParseError as exc:
            logging.warning(f'Scening import: error occured while parsing \'{path.name}\':')
            logging.warning(exc.msg)
            return
        for chapter in root.iter('ChapterAtom'):
            start_element = chapter.find('ChapterTimeStart')
            if start_element is None or start_element.text is None:
                continue
            match = timestamp_pattern.match(start_element.text)
            if match is None:
                continue
            start =  self.main.to_frame(timedelta(
                hours   =   int(match[1]),
                minutes =   int(match[2]),
                seconds = float(match[3])
            ))

            end = None
            end_element = chapter.find('ChapterTimeEnd')
            if end_element is not None and end_element.text is not None:
                match = timestamp_pattern.match(end_element.text)
                if match is not None:
                    end = self.main.to_frame(timedelta(
                        hours   =   int(match[1]),
                        minutes =   int(match[2]),
                        seconds = float(match[3])
                    ))

            label = ''
            label_element = chapter.find('ChapterDisplay/ChapterString')
            if label_element is not None and label_element.text is not None:
                label = label_element.text

            try:
                scening_list.add(start, end, label)
            except ValueError:
                out_of_range_count += 1

    def import_ogm_chapters(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        pattern = re.compile(r'(CHAPTER\d+)=(\d{2}):(\d{2}):(\d{2}(?:\.\d{3})?)\n\1NAME=(.*)', re.RegexFlag.MULTILINE)
        for match in pattern.finditer(path.read_text()):
            t = timedelta(
                hours   =   int(match[2]),
                minutes =   int(match[3]),
                seconds = float(match[4])
            )
            try:
                scening_list.add(self.main.to_frame(t), label=match[5])
            except ValueError:
                out_of_range_count += 1

    def import_qp(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        pattern = re.compile(r'(\d+)\sI|K')
        for match in pattern.findall(path.read_text()):
            try:
                scening_list.add(Frame(match))
            except ValueError:
                out_of_range_count += 1

    def import_matroska_timestamps_v1(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        pattern = re.compile(r'(\d+),(\d+),(\d+(?:\.\d+)?)')

        for match in pattern.finditer(path.read_text()):
            try:
                scening_list.add(Frame(int(match[1])), Frame(int(match[2])), '{:.3f} fps'.format(float(match[3])))
            except ValueError:
                out_of_range_count += 1

    def import_matroska_timestamps_v2(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        timestamps: List[timedelta] = []
        for line in path.read_text().splitlines():
            try:
                timestamps.append(timedelta(milliseconds=float(line)))
            except ValueError:
                continue

        if len(timestamps) < 2:
            logging.warning('Scening import: timestamps file contains less that 2 timestamps, so there\'s nothing to import.')
            return

        deltas = [
            timestamps[i] - timestamps[i - 1]
            for i in range(1, len(timestamps))
        ]
        scene_delta = deltas[0]
        scene_start = Frame(0)
        scene_end: Optional[Frame] = None
        for i in range(1, len(deltas)):
            if abs(round((deltas[i] - scene_delta).total_seconds(), 6)) <= 0.000_001:
                continue
            # TODO: investigate, why offset by -1 is necessary here
            scene_end = Frame(i - 1)
            try:
                scening_list.add(scene_start, scene_end, '{:.3f} fps'.format(1 / scene_delta.total_seconds()))
            except ValueError:
                out_of_range_count += 1
            scene_start = Frame(i)
            scene_end = None
            scene_delta = deltas[i]

        if scene_end is None:
            try:
                scening_list.add(scene_start, Frame(len(timestamps) - 1), '{:.3f} fps'.format(1 / scene_delta.total_seconds()))
            except ValueError:
                out_of_range_count += 1

    def import_tfm(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        class TFMFrame(Frame):
            mic: Optional[int]

        tfm_frame_pattern = re.compile(r'(\d+)\s\((\d+)\)')
        tfm_group_pattern = re.compile(r'(\d+),(\d+)\s\((\d+(?:\.\d+)%)\)')

        log = path.read_text()

        start_pos = log.find('OVR HELP INFORMATION')
        if start_pos == -1:
            logging.warning('Scening import: TFM log doesn\'t contain OVR Help Information.')
            return
        log = log[start_pos:]

        tfm_frames: Set[TFMFrame] = set()
        for match in tfm_frame_pattern.finditer(log):
            tfm_frame = TFMFrame(int(match[1]))
            tfm_frame.mic = int(match[2])
            tfm_frames.add(tfm_frame)

        for match in tfm_group_pattern.finditer(log):
            try:
                scene = scening_list.add(
                    Frame(int(match[1])),
                    Frame(int(match[2])),
                    '{} combed'.format(match[3])
                )
            except ValueError:
                out_of_range_count += 1
                continue

            tfm_frames -= set(range(int(scene.start), int(scene.end) + 1))

        for tfm_frame in tfm_frames:
            try:
                scening_list.add(tfm_frame, label=str(tfm_frame.mic))
            except ValueError:
                out_of_range_count += 1

    def import_xvid(self, path: Path, scening_list: SceningList, out_of_range_count: int) -> None:
        for i, line in enumerate(path.read_text().splitlines()):
            if not line.startswith('i'):
                continue
            try:
                scening_list.add(Frame(i - 3))
            except ValueError:
                out_of_range_count += 1

    # export

    def export_multiline(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            return

        template = self.export_template_lineedit.text()
        export_str = str()

        try:
            for scene in self.current_list:
                export_str += template.format(start=scene.start, end=scene.end, label=scene.label) + '\n'
        except KeyError:
            logging.warning('Scening: export template contains invalid placeholders.')
            self.main.statusbar.showMessage('Export template contains invalid placeholders.', self.main.STATUSBAR_MESSAGE_TIMEOUT)
            return

        self.main.clipboard.setText(export_str)
        self.main.statusbar.showMessage('Scening data exported to the clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

    def export_single_line(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            return

        template = self.export_template_lineedit.text()
        export_str = str()

        try:
            for scene in self.current_list:
                export_str += template.format(start=scene.start, end=scene.end, label=scene.label)
        except KeyError:
            logging.warning('Scening: export template contains invalid placeholders.')
            self.main.statusbar.showMessage('Export template contains invalid placeholders.', self.main.STATUSBAR_MESSAGE_TIMEOUT)
            return

        self.main.clipboard.setText(export_str)
        self.main.statusbar.showMessage('Scening data exported to the clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

    # misc

    def check_add_to_list_possibility(self) -> None:
        self.add_to_list_button.setEnabled(False)

        if not (self.current_list_index != -1
                and (self   .first_frame  is not None
                     or self.second_frame is not None)):
            return

        self.add_to_list_button.setEnabled(True)

    def check_remove_export_possibility(self, checked: Optional[bool] = None) -> None:
        if self.current_list is not None and len(self.current_list) > 0:
            self.remove_last_from_list_button.setEnabled(True)
            self.seek_to_next_button         .setEnabled(True)
            self.seek_to_prev_button         .setEnabled(True)
        else:
            self.remove_last_from_list_button.setEnabled(False)
            self.seek_to_next_button         .setEnabled(False)
            self.seek_to_prev_button         .setEnabled(False)

        if self.current_list is not None and self.main.current_frame in self.current_list:
            self.       add_single_frame_button.setEnabled(False)
            self.remove_at_current_frame_button.setEnabled(True)
        else:
            self.       add_single_frame_button.setEnabled(True)
            self.remove_at_current_frame_button.setEnabled(False)

        if self.export_template_pattern.fullmatch(self.export_template_lineedit.text()) is not None:
            self.export_multiline_button  .setEnabled(True)
            self.export_single_line_button.setEnabled(True)
        else:
            self.export_single_line_button.setEnabled(False)
            self.export_multiline_button  .setEnabled(False)


    def scening_update_status_label(self) -> None:
        first_frame_text  = str(self.first_frame)  if self.first_frame  is not None else ''
        second_frame_text = str(self.second_frame) if self.second_frame is not None else ''
        self.status_label.setText('Scening: {} - {} '.format(first_frame_text, second_frame_text))

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            'first_frame': self.first_frame,
            'second_frame': self.second_frame,
            'label': self.label_lineedit.text(),
            'scening_export_template' : self.export_template_lineedit.text(),
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            first_frame = state['first_frame']
            if first_frame is not None and not isinstance(first_frame, Frame):
                raise TypeError
            self.first_frame = first_frame
        except (KeyError, TypeError):
            logging.warning('Storage loading: Scening: failed to parse Frame 1.')

        if self.first_frame is not None:
            self.toggle_first_frame_button.setChecked(True)

        try:
            second_frame = state['second_frame']
            if second_frame is not None and not isinstance(second_frame, Frame):
                raise TypeError
            self.second_frame = second_frame
        except (KeyError, TypeError):
            logging.warning('Storage loading: Scening: failed to parse Frame 2.')

        if self.second_frame is not None:
            self.toggle_second_frame_button.setChecked(True)

        self.scening_update_status_label()
        self.check_add_to_list_possibility()

        try:
            self.label_lineedit.setText(state['label'])
        except (KeyError, TypeError):
            logging.warning('Storage loading: Scening: failed to parse label.')

        try:
            self.export_template_lineedit.setText(state['scening_export_template'])
        except (KeyError, TypeError):
            logging.warning('Storage loading: Scening: failed to parse export template.')
