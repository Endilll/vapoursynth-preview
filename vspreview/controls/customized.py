from __future__ import annotations

from typing import Callable

from PySide2.QtCore import QAbstractItemModel, Qt
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import (
    QCheckBox, QComboBox, QGraphicsView, QLabel, QLineEdit, QPushButton,
    QSpinBox,
)

from vspreview.core import Output, Property, View
from vspreview.models import GraphicsScene, ListModel


class LineEdit(QLineEdit):
    def __init__(self, parent: View, contents: str = "") -> None:
        super().__init__(contents, parent)
        self._parent = parent
        self._data_context = parent.data_context

    def bind(self, prop: Property, bind_kind: View.BindKind) -> None:
        def get_from_property() -> None:
            value = getattr(self._data_context, prop.name)
            self.setText(str(value))

        def set_to_property(new_text: str) -> None:
            value = prop.ty(new_text)
            setattr(self._data_context, prop.name, value)

        if View.BindKind.is_from_source(bind_kind):
            self._parent.add_property_listener(prop, get_from_property)
            get_from_property()
        if View.BindKind.is_from_view(bind_kind):
            ret = self.textChanged.connect(set_to_property)
            assert ret


class Label(QLabel):
    def __init__(self, parent: View) -> None:
        super().__init__(parent)
        self._parent = parent
        self._data_context = parent.data_context

    def bind(self, prop: Property, bind_kind: View.BindKind) -> None:
        assert bind_kind is View.BindKind.SOURCE_TO_VIEW

        def get_from_property() -> None:
            value = getattr(self._data_context, prop.name)
            if prop.ty is QPixmap:
                self.setPixmap(value)
            else:
                self.setText(str(value))

        self._parent.add_property_listener(prop, get_from_property)
        get_from_property()


class PushButton(QPushButton):
    def bind(self, handler: Callable, bind_kind: View.BindKind) -> None:
        assert bind_kind is View.BindKind.VIEW_TO_SOURCE

        ret = self.clicked.connect(handler)
        assert ret


class ComboBox(QComboBox):
    def __init__(self, parent: View) -> None:
        super().__init__(parent)
        self._parent = parent
        self._data_context = parent.data_context

    def bind_current_item(self, prop: Property, bind_kind: View.BindKind) -> None:
        def get_from_property() -> None:
            value = getattr(self._data_context, prop.name)
            if value is None:
                return
            index = self.model().index_of(value)
            self.setCurrentIndex(index)

        def set_to_property(new_index: int) -> None:
            if new_index != -1:
                new_item = self.model()[new_index]
            else:
                new_item = None
            setattr(self._data_context, prop.name, new_item)

        if View.BindKind.is_from_source(bind_kind):
            self._parent.add_property_listener(prop, get_from_property)
        if View.BindKind.is_from_view(bind_kind):
            ret = self.currentIndexChanged[int].connect(set_to_property)
            assert ret

    def bind_current_index(self, prop: Property, bind_kind: View.BindKind) -> None:
        def get_from_property() -> None:
            value = getattr(self._data_context, prop.name)
            if value is None:
                value = -1
            self.setCurrentIndex(value)

        def set_to_property(new_index: int) -> None:
            value = prop.ty(new_index)
            if value == -1:
                value = None
            setattr(self._data_context, prop.name, value)

        if View.BindKind.is_from_source(bind_kind):
            self._parent.add_property_listener(prop, get_from_property)
        if View.BindKind.is_from_view(bind_kind):
            ret = self.currentIndexChanged[int].connect(set_to_property); assert ret

    def bind_model(self, model: QAbstractItemModel, bind_kind: View.BindKind) -> None:
        assert bind_kind == View.BindKind.SOURCE_TO_VIEW

        self.setModel(model)


class CheckBox(QCheckBox):
    def __init__(self, parent: View) -> None:
        super().__init__(parent)
        self._parent = parent
        self._data_context = parent.data_context

    def bind(self, prop: Property, bind_kind: View.BindKind) -> None:
        def get_from_property() -> None:
            value = getattr(self._data_context, prop.name)
            self.setChecked(bool(value))

        def set_to_property(new_state: int) -> None:
            checked = (new_state == Qt.Checked)  # type: ignore
            value = prop.ty(checked)
            setattr(self._data_context, prop.name, value)

        if View.BindKind.is_from_source(bind_kind):
            self._parent.add_property_listener(prop, get_from_property)
            get_from_property()
        if View.BindKind.is_from_view(bind_kind):
            ret = self.textChanged.connect(set_to_property)
            assert ret


class SpinBox(QSpinBox):
    def __init__(self, parent: View) -> None:
        super().__init__(parent)
        self._parent = parent
        self._data_context = parent.data_context

    def bind_value(self, prop: Property, bind_kind: View.BindKind) -> None:
        def get_from_property() -> None:
            value = int(getattr(self._data_context, prop.name))
            self.setValue(value)

        def set_to_property(new_value: int) -> None:
            value = prop.ty(new_value)
            setattr(self._data_context, prop.name, value)

        if View.BindKind.is_from_source(bind_kind):
            self._parent.add_property_listener(prop, get_from_property)
            get_from_property()
        if View.BindKind.is_from_view(bind_kind):
            ret = self.valueChanged.connect(set_to_property)
            assert ret

    def bind_max_value(self, prop: Property, bind_kind: View.BindKind) -> None:
        assert bind_kind == View.BindKind.SOURCE_TO_VIEW

        def get_from_property() -> None:
            value = int(getattr(self._data_context, prop.name))
            self.setMaximum(value)

        self._parent.add_property_listener(prop, get_from_property)
        get_from_property()


class GraphicsView(QGraphicsView):
    def __init__(self, parent: View, scene: GraphicsScene) -> None:
        super().__init__(parent)
        self._parent = parent
        self.setScene(scene)
        self._data_context = parent.data_context

    def bind_foreground_output(self, prop: Property[Output], bind_kind: View.BindKind) -> None:
        assert bind_kind == View.BindKind.SOURCE_TO_VIEW

        def get_from_property() -> None:
            value = getattr(self._data_context, prop.name)
            if value is None:
                return
            self.scene().switch_to(value)

        self._parent.add_property_listener(prop, get_from_property)
        get_from_property()

    def bind_outputs_model(self, model: ListModel[Output], bind_kind: View.BindKind) -> None:
        assert bind_kind == View.BindKind.SOURCE_TO_VIEW

        self.scene().set_outputs_model(model)
