from __future__ import annotations

from   datetime import timedelta
import logging
from   typing   import Any, cast, List, Mapping, Optional

from PyQt5 import Qt

from vspreview.core  import AbstractMainWindow, AbstractToolbar, Frame, QYAMLObject, Scene
from vspreview.utils import add_shortcut, debug
from vspreview.widgets import ComboBox, Notches

# TODO: make lists combobox editable
# TODO: add template edit for single line export using two fields: one for scene and the other one for list of scenes


class SceningList(Qt.QAbstractListModel, QYAMLObject):
    __slots__ = (
        'name', 'items', 'max_value'
    )
    yaml_tag = '!SceningList'

    def __init__(self, name: str, max_value: Optional[Frame] = None, items: Optional[List[Scene]] = None) -> None:
        super().__init__()
        self.name      = name
        self.max_value = max_value if max_value is not None else Frame(2**31)
        self.items     =     items if     items is not None else []

    def rowCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        return len(self.items)

    def data(self, index: Qt.QModelIndex, role: int = Qt.Qt.UserRole) -> Any:
        if not index.isValid():
            return None
        if index.row() >= len(self.items):
            return None

        if role in (Qt.Qt.DisplayRole,
                    Qt.Qt.EditRole):
            return str(self.items[index.row()])
        if role ==  Qt.Qt.UserRole:
            return self.items[index]
        return None

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int) -> Scene:
        return self.items[i]

    def add(self, start: Frame, end: Optional[Frame] = None) -> None:
    def add(self, start: Frame, end: Optional[Frame] = None, label: str = '') -> Scene:
        from bisect import bisect_right

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
        'items', 'max_value'
    )
    yaml_tag = '!SceningLists'

    def __init__(self, max_value: Optional[Frame] = None, items: Optional[List[SceningList]] = None) -> None:
        super().__init__()
        self.max_value = max_value if max_value is not None else Frame(2**31)
        self.items     =     items if     items is not None else []

    def __getitem__(self, i: int) -> SceningList:
        return self.items[i]

    def __len__(self) -> int:
        return len(self.items)

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
        if not isinstance(value, str):
            return False
        if not role == Qt.Qt.EditRole:
            return False

        self.items[index.row()].name = value
        self.dataChanged.emit(index, index, [role])
        return True

    def insertRow(self, i: int, parent: Qt.QModelIndex = Qt.QModelIndex()) -> bool:
        self.append(i=i)
        return True

    def removeRow(self, i: int, parent: Qt.QModelIndex = Qt.QModelIndex()) -> bool:
        try:
            self.remove_by_index(i)
        except IndexError:
            return False

        return True

    def append(self, name: Optional[str] = None, i: Optional[int] = None) -> SceningList:
        if i is None:
            i = len(self.items)

        self.beginInsertRows(Qt.QModelIndex(), i, i)
        if name is None:
            self.items.insert(i, SceningList('List {}'.format(len(self.items) + 1), self.max_value))
        else:
            self.items.insert(i, SceningList(name, self.max_value))
        self.endInsertRows()
        return self.items[i]

    def remove(self, item: SceningList) -> None:
        self.remove_by_index(self.items.index(item))

    def remove_by_index(self, i: int) -> None:
        if i >= 0 and i < len(self.items):
            self.beginRemoveRows(Qt.QModelIndex(), i, i)
            del(self.items[i])
            self.endRemoveRows()
        else:
            raise IndexError

    def __getstate__(self) -> Mapping[str, Any]:
        return {name: getattr(self, name)
                for name in self.__slots__}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            max_value = state['max_value']
            if not isinstance(max_value, Frame):
                raise TypeError('\'max_value\' of a SceningLists is not a Frame. It\'s most probably corrupted.')

            items = state['items']
            if not isinstance(items, list):
                raise TypeError('\'items\' of a SceningLists is not a List. It\'s most probably corrupted.')
            for item in items:
                if not isinstance(item, SceningList):
                    raise TypeError('One of the items of a SceningLists is not a Bookmark. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('SceningLists lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(max_value, items)  # type: ignore


class SceningListDialog(Qt.QDialog):
    __slots__ = (
        'listview'
    )

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle('Scening List View')

        layout = Qt.QVBoxLayout(self)

        self.listview = Qt.QListView()
        # self.listview.setFixedWidth(200)
        self.listview.setSelectionMode(Qt.QListView.ExtendedSelection)
        layout.addWidget(self.listview)


class SceningToolbar(AbstractToolbar):
    __slots__ = (
        'first_frame', 'second_frame', 'export_template_pattern',
        'scening_list_dialog',
        'lists_combobox', 'add_list_button', 'remove_list_button', 'view_list_button',
        'toggle_first_frame_button', 'toggle_second_frame_button',
        'add_to_list_button', 'remove_last_from_list_button',
        'export_single_line_button', 'export_template_lineedit', 'export_multiline_button',
        'status_label',
        'toggle_button'
    )

    def __init__(self, main_window: AbstractMainWindow) -> None:
        super().__init__(main_window)
        self.setup_ui()

        self.first_frame : Optional[Frame] = None
        self.second_frame: Optional[Frame] = None
        self.export_template_scene_pattern  = re.compile(r'.*(?:{start}|{end}|{label}).*')
        self.export_template_scenes_pattern = re.compile(r'.+')

        self.scening_update_status_label()
        self.scening_list_dialog = SceningListDialog()

        self.supported_file_types = {
            'Aegisub Project (*.ass)'       : self.import_ass,
            'CUE Sheet (*.cue)'             : self.import_cue,
            'DGIndex Project (*.dgi)'       : self.import_dgi,
            'Matroska Timestamps v1 (*.txt)': self.import_matroska_timestamps_v1,
            'Matroska Timestamps v2 (*.txt)': self.import_matroska_timestamps_v2,
            'Matroska XML Chapters (*.xml)' : self.import_matroska_xml_chapters,
            'OGM Chapters (*.txt)'          : self.import_ogm_chapters,
            'TFM Log (*.txt)'               : self.import_tfm,
            'x264 QP File (*.qp)'           : self.import_qp,
            'XviD Log (*.txt)'              : self.import_xvid,
        }

        self.toggle_button                 .clicked.connect(self.on_toggle)
        self.add_list_button               .clicked.connect(self.on_add_list_clicked)
        self.add_single_frame_button       .clicked.connect(self.on_add_single_frame_clicked)
        self.add_to_list_button            .clicked.connect(self.on_add_to_list_clicked)
        self.export_multiline_button       .clicked.connect(self.export_multiline)  # type: ignore
        self.export_single_line_button     .clicked.connect(self.export_single_line)  # type: ignore
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
        self.export_template_scene_lineedit .textChanged.connect(self.check_remove_export_possibility)
        self.export_template_scenes_lineedit.textChanged.connect(self.check_remove_export_possibility)

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

    def setup_ui(self) -> None:
        self.setVisible(False)
        layout = Qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.items_combobox = ComboBox(self)
        # self.items_combobox.setEditable(True)
        self.items_combobox.setDuplicatesEnabled(True)
        self.items_combobox.setSizeAdjustPolicy(ComboBox.AdjustToContents)
        layout.addWidget(self.items_combobox)

        self.add_list_button = Qt.QPushButton(self)
        self.add_list_button.setText('Add List')
        layout.addWidget(self.add_list_button)

        self.remove_list_button = Qt.QPushButton(self)
        self.remove_list_button.setText('Remove List')
        self.remove_list_button.setEnabled(False)
        layout.addWidget(self.remove_list_button)

        self.view_list_button = Qt.QPushButton(self)
        self.view_list_button.setText('View List')
        self.view_list_button.setEnabled(False)
        layout.addWidget(self.view_list_button)

        self.import_file_button = Qt.QPushButton(self)
        self.import_file_button.setText('Import File')
        layout.addWidget(self.import_file_button)

        separator = Qt.QFrame(self)
        separator.setFrameShape(Qt.QFrame.VLine)
        separator.setFrameShadow(Qt.QFrame.Sunken)
        layout.addWidget(separator)

        self.seek_to_prev_button = Qt.QPushButton(self)
        self.seek_to_prev_button.setText('⏪')
        layout.addWidget(self.seek_to_prev_button)

        self.seek_to_next_button = Qt.QPushButton(self)
        self.seek_to_next_button.setText('⏩')
        layout.addWidget(self.seek_to_next_button)

        separator = Qt.QFrame(self)
        separator.setFrameShape(Qt.QFrame.VLine)
        separator.setFrameShadow(Qt.QFrame.Sunken)
        layout.addWidget(separator)

        self.add_single_frame_button = Qt.QPushButton(self)
        self.add_single_frame_button.setText('Add Single Frame')
        layout.addWidget(self.add_single_frame_button)

        self.toggle_first_frame_button = Qt.QPushButton(self)
        self.toggle_first_frame_button.setText('Frame 1')
        self.toggle_first_frame_button.setCheckable(True)
        layout.addWidget(self.toggle_first_frame_button)

        self.toggle_second_frame_button = Qt.QPushButton(self)
        self.toggle_second_frame_button.setText('Frame 2')
        self.toggle_second_frame_button.setCheckable(True)
        layout.addWidget(self.toggle_second_frame_button)

        self.label_lineedit = Qt.QLineEdit(self)
        self.label_lineedit.setPlaceholderText('Label')
        layout.addWidget(self.label_lineedit)

        self.add_to_list_button = Qt.QPushButton(self)
        self.add_to_list_button.setText('Add to List')
        self.add_to_list_button.setEnabled(False)
        layout.addWidget(self.add_to_list_button)

        self.remove_last_from_list_button = Qt.QPushButton(self)
        self.remove_last_from_list_button.setText('Remove Last')
        self.remove_last_from_list_button.setEnabled(False)
        layout.addWidget(self.remove_last_from_list_button)

        self.remove_at_current_frame_button = Qt.QPushButton(self)
        self.remove_at_current_frame_button.setText('Remove at Current Frame')
        self.remove_at_current_frame_button.setEnabled(False)
        layout.addWidget(self.remove_at_current_frame_button)

        separator = Qt.QFrame(self)
        separator.setFrameShape(Qt.QFrame.VLine)
        separator.setFrameShadow(Qt.QFrame.Sunken)
        layout.addWidget(separator)

        self.export_template_scene_lineedit = Qt.QLineEdit(self)
        # self.export_template_scene_lineedit.setSizePolicy(Qt.QSizePolicy(Qt.QSizePolicy.Policy.Expanding, Qt.QSizePolicy.Policy.Fixed))
        self.export_template_scene_lineedit.setToolTip(r'Use {start} and {end} as placeholders. Both are valid for single frame scenes. {label} is available, too.')
        self.export_template_scene_lineedit.setPlaceholderText('Scene template')
        layout.addWidget(self.export_template_scene_lineedit)

        self.export_multiline_button = Qt.QPushButton(self)
        self.export_multiline_button.setText('Export Multiline')
        self.export_multiline_button.setEnabled(False)
        layout.addWidget(self.export_multiline_button)

        self.export_template_scenes_lineedit = Qt.QLineEdit(self)
        self.export_template_scenes_lineedit.setToolTip(r'Joiner for scenes exported using previous template to form single line.')
        self.export_template_scenes_lineedit.setPlaceholderText('Scenes joiner')
        layout.addWidget(self.export_template_scenes_lineedit)

        self.export_single_line_button = Qt.QPushButton(self)
        self.export_single_line_button.setText('Export Single Line')
        self.export_single_line_button.setEnabled(False)
        layout.addWidget(self.export_single_line_button)

        layout.addStretch()
        layout.addStretch()

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
        self.notchesChanged.emit(self)

    def on_current_frame_changed(self, frame: Frame, t: timedelta) -> None:
        self.check_remove_export_possibility()

    def get_notches(self) -> Notches:
        marks = Notches()
        if self.current_list is None:
            return marks
        for scene in self.current_list:
            marks.add(scene, cast(Qt.QColor, Qt.Qt.green))
        return marks

    @property
    def current_list(self) -> SceningList:
        return cast(SceningList, self.items_combobox.currentData())

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
        if not 0 <= index < len(self.current_lists):
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
            self.scening_list_dialog.listview.setModel(self.current_list)

        if old_index != -1:
            try:
                self.current_lists[old_index].rowsInserted.disconnect(self._on_list_items_changed)  # type: ignore
                self.current_lists[old_index].rowsRemoved .disconnect(self._on_list_items_changed)  # type: ignore
            except (IndexError, TypeError):
                pass

        self.check_add_to_list_possibility()
        self.check_remove_export_possibility()
        self.notchesChanged.emit(self)

    def on_list_items_changed(self, parent: Qt.QModelIndex, first: int, last: int) -> None:
        self.notchesChanged.emit(self)

    def on_remove_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.current_lists.remove(self.current_list_index)

    def on_view_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.scening_list_dialog.listview.setModel(self.current_list)
        self.scening_list_dialog.open()

    def switch_list(self, index: int) -> None:
        try:
            self.current_list_index = index
        except IndexError:
            pass

    # seeking

    def on_seek_to_next_clicked(self, checked: Optional[bool] = None) -> None:
        next_frame = self.current_list.get_next_frame(self.main.current_frame)
        if next_frame is None:
            return
        self.main.current_frame = next_frame

    def on_seek_to_prev_clicked(self, checked: Optional[bool] = None) -> None:
        next_frame = self.current_list.get_prev_frame(self.main.current_frame)
        if next_frame is None:
            return
        self.main.current_frame = next_frame

    # scene management

    def on_add_single_frame_clicked(self, checked: Optional[bool] = None) -> None:
        if self.current_list is None:
            self.on_add_list_clicked()
        self.current_list.add(self.main.current_frame)
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
        for scene in self.current_list:
            if (scene.start == self.main.current_frame
                    or scene.end == self.main.current_frame):
                self.current_list.remove(scene)

        self.remove_at_current_frame_button.clearFocus()
        self.check_remove_export_possibility()

    def on_remove_last_from_list_clicked(self, checked: Optional[bool] = None) -> None:
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
            if abs(round((deltas[i] - scene_delta).total_seconds(), 6)) <= 0.000001:
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

    def export_multiline(self, checked: Optional[bool] = None, clipboard: bool = True) -> str:
        template = self.export_template_scene_lineedit.text()
        export_str = str()

        for scene in self.current_list:
            export_str += template.format(start=scene.start, end=scene.end, label=scene.label) + '\n'

        if clipboard is True:
            self.main.clipboard.setText(export_str)
            self.main.statusbar.showMessage('Scening data exported to the clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

        return export_str

    def export_single_line(self, checked: Optional[bool] = None, clipboard: bool = True) -> str:
        joiner = self.export_template_scenes_lineedit.text()
        export_str = joiner.join(self.export_multiline().splitlines())

        if clipboard is True:
            self.main.clipboard.setText(export_str)
            self.main.statusbar.showMessage('Scening data exported to the clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

        return export_str

    # misc

    def check_add_to_list_possibility(self) -> None:
        self.add_to_list_button.setEnabled(False)

        if not (self.current_list_index != -1
                and (self   .first_frame  is not None
                     or self.second_frame is not None)):
            return

        self.add_to_list_button.setEnabled(True)

    def check_remove_export_possibility(self, checked: Optional[bool] = None) -> None:
        self.add_single_frame_button       .setEnabled(True)
        self.export_single_line_button     .setEnabled(False)
        self.export_multiline_button       .setEnabled(False)
        self.remove_at_current_frame_button.setEnabled(False)
        self.remove_last_from_list_button  .setEnabled(False)

        if not (self.current_list_index is not None
                and self.current_list_index != -1
                and len(self.current_list) > 0):
            return

        self.remove_last_from_list_button.setEnabled(True)

        for scene in self.current_list:
            if (scene.start == self.main.current_frame
                    or scene.end == self.main.current_frame):
                self.       add_single_frame_button.setEnabled(False)
                self.remove_at_current_frame_button.setEnabled(True)
                break

        if self.export_template_scene_pattern .fullmatch(self.export_template_scene_lineedit .text()) is not None:
            self.export_multiline_button  .setEnabled(True)
        if self.export_template_scenes_pattern.fullmatch(self.export_template_scenes_lineedit.text()) is not None:
            self.export_single_line_button.setEnabled(True)

    def scening_update_status_label(self) -> None:
        first_frame_text  = str(self.first_frame)  if self.first_frame  is not None else ''
        second_frame_text = str(self.second_frame) if self.second_frame is not None else ''
        self.status_label.setText('Scening: {} - {} '.format(first_frame_text, second_frame_text))

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            'first_frame': self.first_frame,
            'second_frame': self.second_frame,
            'label': self.label_lineedit.text(),
            'scening_export_scene_template' : self.export_template_scene_lineedit .text(),
            'scening_export_scenes_template': self.export_template_scenes_lineedit.text(),
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
            self.export_template_scene_lineedit.setText(state['scening_export_scene_template'])
        except (KeyError, TypeError):
            logging.warning('Storage loading: Scening: failed to parse scene export template.')

        try:
            self.export_template_scenes_lineedit.setText(state['scening_export_scenes_template'])
        except (KeyError, TypeError):
            logging.warning('Storage loading: Scening: failed to parse scenes export template.')
