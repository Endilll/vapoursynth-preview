from __future__ import annotations

from PySide2.QtCore    import QModelIndex
from PySide2.QtWidgets import QGraphicsScene

from vspreview.core import Output
from .generic import ListModel


class GraphicsScene(QGraphicsScene):
    def set_outputs_model(self, model: ListModel[Output]) -> None:
        def add_output(output: Output) -> None:
            output.graphics_item = self.addPixmap(output.render_frame(output.current_frame))
            output.graphics_item.hide()  # type: ignore

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
            item.hide()
        if output.graphics_item is None:
            return
        output.graphics_item.show()  # type: ignore
