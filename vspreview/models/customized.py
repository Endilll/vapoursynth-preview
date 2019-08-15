from __future__ import annotations

from PySide2.QtCore    import QModelIndex
from PySide2.QtGui     import QPixmap
from PySide2.QtWidgets import QGraphicsScene

from vspreview.core import GraphicsItem, Output
from .generic import ListModel


class GraphicsScene(QGraphicsScene):
    def set_outputs_model(self, model: ListModel[Output]) -> None:
        def add_output(output: Output) -> None:
            graphics_item = self.addPixmap(QPixmap())
            graphics_item.hide()
            output.graphics_item = graphics_item

        def remove_output(output: Output) -> None:
            if output.graphics_item is None:
                return
            self.removeItem(output.graphics_item)
            output.graphics_item = None

        def on_outputs_added(index: QModelIndex, first: int, last: int) -> None:
            for i in range(first, last + 1):
                add_output(model[i])

        def on_outputs_removed(index: QModelIndex, first: int, last: int) -> None:
            if last - first + 1 == len(model):
                self.clear()  # type: ignore
                return

            for i in range(first, last + 1):
                remove_output(model[i])

        for output in model:
            add_output(output)

        ret = model.rowsInserted.connect(on_outputs_added); assert ret
        ret = model.rowsAboutToBeRemoved.connect(on_outputs_removed); assert ret

    def switch_to(self, output: Output) -> None:
        for item in self.items():
            if item is output.graphics_item:
                continue
            item.hide()
        if output.graphics_item is None or output.graphics_item.visible:
            return
        output.graphics_item.show()

    def addPixmap(self, pixmap: QPixmap) -> GraphicsItem:
        item = GraphicsItem(pixmap)
        self.addItem(item)
        return item
