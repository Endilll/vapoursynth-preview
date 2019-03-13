from __future__ import annotations

from   bisect   import bisect_left, bisect_right, insort
from   datetime import timedelta
import logging
from   pathlib  import Path
import re
from   typing   import Any, Iterator, List, Mapping, Optional, Union

from PyQt5 import Qt

from vspreview.core  import AbstractMainWindow, AbstractToolbar, Bookmark, Frame, QYAMLObject
from vspreview.utils import add_shortcut, debug, fire_and_forget, main_window, set_status_label

# TODO: test case when all bookmarks are out of range


class BookmarksToolbar(AbstractToolbar):
    __slots__ = (
        'supported_file_types', 'current_bookmark',
        'seek_to_prev_button', 'toggle_button', 'seek_to_next_button',
        'label_lineedit', 'load_from_file_button', 'clear_button',
        'switch_button'
    )

    def __init__(self, main: AbstractMainWindow) -> None:
        super().__init__(main)
        self.setup_ui()

        self.current_bookmark: Optional[Bookmark] = None
        self.supported_file_types = {
            'Aegisub Project (*.ass)'  : self.load_from_ass,
            'Chapters File (*.txt)'    : self.load_from_chapters,
            'DGIndexNV Project (*.dgi)': self.load_from_dgi,
            'x264 QP File (*.qp)'      : self.load_from_qp
        }

        self.switch_button        .clicked.connect(self.on_toggle)
        self.toggle_button        .clicked.connect(self.on_toggle_clicked)
        self.seek_to_prev_button  .clicked.connect(self.seek_to_prev_clicked)
        self.seek_to_next_button  .clicked.connect(self.seek_to_next_clicked)
        self.clear_button         .clicked.connect(self.on_clear_clicked)
        self.label_lineedit   .textChanged.connect(self.on_label_changed)
        self.load_from_file_button.clicked.connect(self.on_load_clicked)

        add_shortcut(Qt.Qt.CTRL + Qt.Qt.Key_Space, self.      toggle_button.click)
        add_shortcut(Qt.Qt.CTRL + Qt.Qt.Key_Left , self.seek_to_prev_button.click)
        add_shortcut(Qt.Qt.CTRL + Qt.Qt.Key_Right, self.seek_to_next_button.click)

    def setup_ui(self) -> None:
        self.setVisible(False)
        layout = Qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.seek_to_prev_button = Qt.QPushButton(self)
        self.seek_to_prev_button.setText('⏪')
        layout.addWidget(self.seek_to_prev_button)

        self.toggle_button = Qt.QPushButton(self)
        self.toggle_button.setText('Toggle Bookmark')
        self.toggle_button.setCheckable(True)
        layout.addWidget(self.toggle_button)

        self.seek_to_next_button = Qt.QPushButton(self)
        self.seek_to_next_button.setText('⏩')
        layout.addWidget(self.seek_to_next_button)

        self.label_lineedit = Qt.QLineEdit(self)
        self.label_lineedit.setEnabled(False)
        layout.addWidget(self.label_lineedit)

        self.load_from_file_button = Qt.QPushButton(self)
        self.load_from_file_button.setText('Load')
        layout.addWidget(self.load_from_file_button)

        self.clear_button = Qt.QPushButton(self)
        self.clear_button.setText('Clear')
        layout.addWidget(self.clear_button)

        layout.addStretch()
        layout.addStretch()
        layout.addStretch()

        # swich button for main toolbar

        self.switch_button = Qt.QPushButton(self.main.central_widget)
        self.switch_button.setText('Bookmarks')
        self.switch_button.setCheckable(True)

    def on_toggle(self, new_state: bool) -> None:
        # invoking order matters
        self.setVisible(new_state)
        self.resize_main_window(new_state)

    def on_current_frame_changed(self, frame: Frame, t: Optional[timedelta] = None) -> None:
        if frame in self.main.current_output.bookmarks:
            self.current_bookmark = self.main.current_output.bookmarks[frame]
            self.toggle_button.setChecked(True)
            self.label_lineedit.setEnabled(True)
            self.label_lineedit.setText(self.current_bookmark.label)
        else:
            self.current_bookmark = None
            self.toggle_button.setChecked(False)
            self.label_lineedit.setEnabled(False)
            self.label_lineedit.setText('')

    def on_current_output_changed(self, index: int) -> None:
        pass


    def on_clear_clicked(self) -> None:
        self.main.current_output.bookmarks.clear()
        self.main.timeline.repaint()
        self.toggle_button.setChecked(False)

    def on_toggle_clicked(self, checked: bool) -> None:
        if checked:
            self.main.current_output.bookmarks.add(Bookmark(self.main.current_frame))
        else:
            self.main.current_output.bookmarks.remove(Bookmark(self.main.current_frame))
        self.on_current_frame_changed(self.main.current_frame)

    def seek_to_prev_clicked(self) -> None:
        prev_bookmark = self.main.current_output.bookmarks.get_prev(self.main.current_frame)
        if prev_bookmark is not None:
            self.main.current_frame = prev_bookmark.frame

    def seek_to_next_clicked(self) -> None:
        next_bookmark = self.main.current_output.bookmarks.get_next(self.main.current_frame)
        if next_bookmark is not None:
            self.main.current_frame = next_bookmark.frame

    def on_label_changed(self, label: str) -> None:
        if self.current_bookmark is not None:
            self.current_bookmark.label = label

    def on_load_clicked(self, checked: Optional[bool] = None) -> None:
        # filter_str = ''.join([file_type + ';;' for file_type in self.supported_file_types.keys()])
        # filter_str = filter_str[0:-2]
        filter_str = ';;'.join(self.supported_file_types.keys())
        path_strs, file_type = Qt.QFileDialog.getOpenFileNames(self.main, caption='Open chapters file', filter=filter_str)

        paths = [Path(path_str) for path_str in path_strs]
        for path in paths:
            self.supported_file_types[file_type](path)  # type: ignore

    # FIXME: fire_and_forget breaks the method
    # @fire_and_forget
    # FIXME: status label decorator breaks the method
    # @set_status_label('Loading bookmarks')
    def load_from_chapters(self, path: Path) -> None:
        pattern = re.compile(r'(CHAPTER\d+)=(\d{2}):(\d{2}):(\d{2})(?:(?:\.|:)(\d{3}))?\n\1NAME=(.*)', re.RegexFlag.MULTILINE)
        failed = 0
        for match in pattern.findall(path.read_text()):
            if match[4] == '':
                t = timedelta(
                    hours   = int(match[1]),
                    minutes = int(match[2]),
                    seconds = int(match[3])
                )
            else:
                t = timedelta(
                    hours        = int(match[1]),
                    minutes      = int(match[2]),
                    seconds      = int(match[3]),
                    milliseconds = int(match[4])
                )

            bookmark = Bookmark(self.main.timedelta_to_frame(t), match[5])

            if not self.main.current_output.bookmarks.add(bookmark):
                failed += 1
        if failed > 0:
            logging.warning(f'Bookmarks loading: {failed} bookmarks were out of range of output, so they were dropped.')

    @fire_and_forget
    # @set_status_label('Loading bookmarks')
    def load_from_dgi(self, path: Path) -> None:
        pattern = re.compile(r'IDR\s\d+\n(\d+):FRM', re.RegexFlag.MULTILINE)
        failed = 0
        for match in pattern.findall(path.read_text()):
            if not self.main.current_output.bookmarks.add(Bookmark(match)):
                failed += 1
        if failed > 0:
            logging.warning(f'Bookmarks loading: {failed} bookmarks were out of range of output, so they were dropped.')

    @fire_and_forget
    # @set_status_label('Loading bookmarks')
    def load_from_qp(self, path: Path) -> None:
        pattern = re.compile(r'(\d+)\sI|K')
        failed = 0
        for match in pattern.findall(path.read_text()):
            if not self.main.current_output.bookmarks.add(Bookmark(match)):
                failed += 1
        if failed > 0:
            logging.warning(f'Bookmarks loading: {failed} bookmarks were out of range of output, so they were dropped.')

    @fire_and_forget
    # @set_status_label('Loading bookmarks')
    def load_from_ass(self, path: Path) -> None:
        import pysubs2

        failed = 0

        subs = pysubs2.load(str(path))
        for line in subs:
            t = timedelta(milliseconds=line.start)
            if not self.main.current_output.bookmarks.add(Bookmark(self.main.timedelta_to_frame(t))):
                failed += 1
        if failed > 0:
            logging.warning(f'Bookmarks loading: {failed} bookmarks were out of range of output, so they were dropped.')


class Bookmarks(Qt.QAbstractListModel, QYAMLObject):
    from yaml import Dumper, Loader, Node

    __slots__ = ('items', 'max_value')
    yaml_tag = '!Bookmarks'

    changed = Qt.pyqtSignal()

    def __init__(self, max_value: Optional[Frame] = None, items: Optional[List[Bookmark]] = None) -> None:
        super().__init__()
        # TODO: come with a better solution for missing integer infinity
        self.max_value = max_value if max_value is not None else Frame(2**31)
        self.items     =     items if     items is not None else []

    def __getitem__(self, i: Union[int, Frame]) -> Bookmark:
        if isinstance(i, Frame):
            for bookmark in self.items:
                if bookmark == i:
                    return bookmark
        if isinstance(i, int):
            return self.items[i]

        logging.debug(type(i))
        raise TypeError()

    def __iter__(self) -> Iterator[Bookmark]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def add(self, new_item: Bookmark) -> bool:
        # https://github.com/python/mypy/issues/4610
        if (new_item <= self.max_value  # type: ignore
                and new_item not in self.items):
            insort(self.items, new_item)
            self.changed.emit()
            return True
        else:
            return False

    def clear(self) -> None:
        self.items.clear()
        self.changed.emit()

    def data(self, index: Qt.QModelIndex, role: int = Qt.Qt.UserRole) -> Any:
        if not index.isValid():
            return None

        if index.row() >= len(self.items):
            return None

        if   role == Qt.Qt.DisplayRole:
            return str(self.items[index.row()])
        elif role == Qt.Qt.UserRole:
            return self.items[index.row()]
        else:
            return None

    def get_next(self, item: Union[Bookmark, Frame]) -> Optional[Bookmark]:
        i = bisect_right(self.items, item)
        if i != len(self.items):
            next_item = self.items[i]
            # https://github.com/python/mypy/issues/4610
            if next_item <= self.max_value:  # type: ignore
                return next_item
        return None

    def get_prev(self, item: Union[Bookmark, Frame]) -> Optional[Bookmark]:
        i = bisect_left(self.items, item)
        if i != 0:
            return self.items[i - 1]
        return None

    def remove(self, bookmark: Bookmark) -> None:
        self.items.remove(bookmark)
        self.changed.emit()

    def rowCount(self, parent: Qt.QModelIndex = Qt.QModelIndex()) -> int:
        return len(self.items)

    def __getstate__(self) -> Mapping[str, Any]:
        return {name: getattr(self, name)
                for name in self.__slots__}

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            max_value = state['max_value']
            if not isinstance(max_value, Frame):
                raise TypeError('\'max_value\' of a Bookmarks is not a Frame. It\'s most probably corrupted.')

            items = state['items']
            if not isinstance(items, list):
                raise TypeError('\'items\' of a Bookmarks is not a List. It\'s most probably corrupted.')
            for item in items:
                if not isinstance(item, Bookmark):
                    raise TypeError('One of the items of Bookmarks is not a Bookmark. It\'s most probably corrupted.')
        except KeyError:
            raise KeyError('Bookmarks lacks one or more of its fields. It\'s most probably corrupted. Check those: {}.'.format(', '.join(self.__slots__)))

        self.__init__(max_value, items)  # type: ignore
