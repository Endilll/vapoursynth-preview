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
        from bisect import bisect_right

        scene = Scene(start, end)

        if scene in self.items:
            return

        if scene.end > self.max_value:
            raise ValueError('New Scene is out of bounds of output')

        index = bisect_right(self.items, scene)
        self.beginInsertRows(Qt.QModelIndex(), index, index)
        self.items.insert(index, scene)
        self.endInsertRows()

    def remove(self, item: Scene) -> None:
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
        'switch_button'
    )

    def __init__(self, main_window: AbstractMainWindow) -> None:
        import re

        super().__init__(main_window)
        self.setup_ui()

        self.first_frame : Optional[Frame] = None
        self.second_frame: Optional[Frame] = None
        self.export_template_pattern = re.compile(r'.*(?:{start}.*{end}|{end}.*{start}).*')

        self.scening_update_status_label()
        self.scening_list_dialog = SceningListDialog()

        self.switch_button               .clicked.connect(self.on_toggle)
        self.items_combobox  .currentIndexChanged.connect(self.on_lists_current_index_changed)
        self.add_list_button             .clicked.connect(self.on_add_list_clicked)
        self.remove_list_button          .clicked.connect(self.on_remove_list_clicked)
        self.view_list_button            .clicked.connect(self.on_view_list_clicked)
        self.toggle_first_frame_button   .clicked.connect(self.on_first_frame_clicked)
        self.toggle_second_frame_button  .clicked.connect(self.on_second_frame_clicked)
        self.add_to_list_button          .clicked.connect(self.on_add_to_list_clicked)
        self.remove_last_from_list_button.clicked.connect(self.on_remove_last_from_list_clicked)
        self.export_single_line_button   .clicked.connect(self.export_single_line)
        self.export_template_lineedit.textChanged.connect(self.check_remove_export_possibility)
        self.export_multiline_button     .clicked.connect(self.export_multiline)

        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_1, lambda: self.scening_switch_list(0))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_2, lambda: self.scening_switch_list(1))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_3, lambda: self.scening_switch_list(2))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_4, lambda: self.scening_switch_list(3))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_5, lambda: self.scening_switch_list(4))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_6, lambda: self.scening_switch_list(5))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_7, lambda: self.scening_switch_list(6))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_8, lambda: self.scening_switch_list(7))
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_9, lambda: self.scening_switch_list(8))
        add_shortcut(              Qt.Qt.Key_Q, self.toggle_first_frame_button   .click)
        add_shortcut(              Qt.Qt.Key_W, self.toggle_second_frame_button  .click)
        add_shortcut(              Qt.Qt.Key_E, self.add_to_list_button          .click)
        add_shortcut(              Qt.Qt.Key_R, self.remove_last_from_list_button.click)

    def setup_ui(self) -> None:
        self.setVisible(False)
        layout = Qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.items_combobox = Qt.QComboBox(self)
        # self.items_combobox.setEditable(True)
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

        separator = Qt.QFrame(self)
        separator.setFrameShape(Qt.QFrame.VLine)
        separator.setFrameShadow(Qt.QFrame.Sunken)
        layout.addWidget(separator)

        self.toggle_first_frame_button = Qt.QPushButton(self)
        self.toggle_first_frame_button.setText('Frame 1')
        self.toggle_first_frame_button.setCheckable(True)
        layout.addWidget(self.toggle_first_frame_button)

        self.toggle_second_frame_button = Qt.QPushButton(self)
        self.toggle_second_frame_button.setText('Frame 2')
        self.toggle_second_frame_button.setCheckable(True)
        layout.addWidget(self.toggle_second_frame_button)

        self.add_to_list_button = Qt.QPushButton(self)
        self.add_to_list_button.setText('Add to List')
        self.add_to_list_button.setEnabled(False)
        layout.addWidget(self.add_to_list_button)

        self.remove_last_from_list_button = Qt.QPushButton(self)
        self.remove_last_from_list_button.setText('Remove Last')
        self.remove_last_from_list_button.setEnabled(False)
        layout.addWidget(self.remove_last_from_list_button)

        separator2 = Qt.QFrame(self)
        separator2.setFrameShape(Qt.QFrame.VLine)
        separator2.setFrameShadow(Qt.QFrame.Sunken)
        layout.addWidget(separator2)

        self.export_single_line_button = Qt.QPushButton(self)
        self.export_single_line_button.setText('Export Single Line')
        self.export_single_line_button.setEnabled(False)
        layout.addWidget(self.export_single_line_button)

        self.export_template_lineedit = Qt.QLineEdit()
        # self.export_template_lineedit.setSizePolicy(Qt.QSizePolicy(Qt.QSizePolicy.Policy.Expanding, Qt.QSizePolicy.Policy.Fixed))
        self.export_template_lineedit.setToolTip(r'Use {start} and {end} as placeholders. Both are valid for single frames, too.')
        layout.addWidget(self.export_template_lineedit)

        self.export_multiline_button = Qt.QPushButton(self)
        self.export_multiline_button.setText('Export Using Template')
        self.export_multiline_button.setEnabled(False)
        layout.addWidget(self.export_multiline_button)

        layout.addStretch()
        layout.addStretch()

        # statusbar label

        self.status_label = Qt.QLabel(self)
        self.status_label.setVisible(False)
        self.main.statusbar.addPermanentWidget(self.status_label)

        # switch button for main layout

        self.switch_button = Qt.QPushButton(self.main.central_widget)
        self.switch_button.setText('Scening')
        self.switch_button.setCheckable(True)

    def on_toggle(self, new_state: bool) -> None:
        if new_state is True:
            self.check_add_to_list_possibility()
            self.check_remove_export_possibility()

        self.status_label.setVisible(new_state)
        # invoking order matters
        self.setVisible(new_state)
        self.resize_main_window(new_state)

    def on_current_frame_changed(self, frame: Frame, t: timedelta) -> None:
        pass

    def on_current_output_changed(self, index: int) -> None:
        self.items_combobox.setModel(self.main.current_output.scening_lists)

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

    @property
    def current_list_index(self) -> int:
        return self.items_combobox.currentIndex()


    def check_add_to_list_possibility(self) -> None:
        if (self.current_list_index != -1
                and (self   .first_frame  is not None
                     or self.second_frame is not None)):
            self.add_to_list_button.setEnabled(True)
        else:
            self.add_to_list_button.setEnabled(False)

    def check_remove_export_possibility(self, checked: Optional[bool] = None) -> None:
        self.export_single_line_button   .setEnabled(False)
        self.export_multiline_button     .setEnabled(False)
        self.remove_last_from_list_button.setEnabled(False)

        if (self.current_list_index is not None
                and self.current_list_index != -1
                and len(self.current_list) > 0):
            self.export_single_line_button.setEnabled(True)
            self.remove_last_from_list_button.setEnabled(True)

            if self.export_template_pattern.fullmatch(self.export_template_lineedit.text()) is not None:
                self.export_multiline_button.setEnabled(True)

    def export_multiline(self, checked: Optional[bool] = None) -> None:
        export_str = str()
        template = self.export_template_lineedit.text()

        for scene in self.current_list:
            export_str += template.format(start=scene.start, end=scene.end) + '\n'

        self.main.clipboard.setText(export_str)
        self.main.statusbar.showMessage('Scening data exported to the clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

    def export_single_line(self, checked: Optional[bool] = None) -> None:
        export_str = str()

        for scene in self.current_list:
            if scene.start == scene.end:
                export_str += '{},'.format(scene.start)
            else:
                export_str += '[{},{}],'.format(scene.start, scene.end)
        export_str.rstrip()

        self.main.clipboard.setText(export_str)
        self.main.statusbar.showMessage('Scening data exported to the clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

    def on_add_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.main.current_output.scening_lists.append()

    def on_add_to_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.current_list.add(self.first_frame, self.second_frame)  # type: ignore
        if self.toggle_first_frame_button.isChecked():
            self.toggle_first_frame_button.click()
        if self.toggle_second_frame_button.isChecked():
            self.toggle_second_frame_button.click()
        self.add_to_list_button.setEnabled(False)

        self.check_remove_export_possibility()

    def on_first_frame_clicked(self, checked: bool) -> None:
        if checked:
            self.first_frame = self.main.current_frame
        else:
            self.first_frame = None
        self.scening_update_status_label()
        self.check_add_to_list_possibility()

    def on_lists_current_index_changed(self, index: int) -> None:
        if index == -1:
            self.remove_list_button.setEnabled(False)
            self.  view_list_button.setEnabled(False)
        else:
            self.remove_list_button.setEnabled(True)
            self.  view_list_button.setEnabled(True)

        self.check_add_to_list_possibility()
        self.check_remove_export_possibility()

    def on_remove_last_from_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.current_list.remove(self.current_list[-1])
        self.check_remove_export_possibility()

    def on_remove_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.main.current_output.scening_lists.remove_by_index(self.current_list_index)

    def on_second_frame_clicked(self, checked: bool) -> None:
        if checked:
            self.second_frame = self.main.current_frame
        else:
            self.second_frame = None
        self.scening_update_status_label()
        self.check_add_to_list_possibility()

    def on_view_list_clicked(self, checked: Optional[bool] = None) -> None:
        self.scening_list_dialog.listview.setModel(self.current_list)
        self.scening_list_dialog.open()

    def scening_switch_list(self, index: int) -> None:
        if index >= 0 and index < len(self.main.current_output.scening_lists):
            self.items_combobox.setCurrentIndex(index)

    def scening_update_status_label(self) -> None:
        first_frame_text  = str(self.first_frame)  if self.first_frame  is not None else ''
        second_frame_text = str(self.second_frame) if self.second_frame is not None else ''
        self.status_label.setText('Scening: {} - {} '.format(first_frame_text, second_frame_text))

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            'scening_export_template': self.export_template_lineedit.text(),
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            self.export_template_lineedit.setText(state['scening_export_template'])
        except (KeyError, TypeError):
            logging.warning('Storage loading: failed to parse save file name template.')
