import ctypes
import logging
from typing import Dict, List, TypeVar, Union

from PyQt5 import Qt
import vapoursynth as vs

from vspreview.core    import AbstractMainWindow, AbstractToolbar, Output
from vspreview.utils   import set_qobject_names
from vspreview.widgets import ColorView


Number = TypeVar('Number', int, float)


class PipetteToolbar(AbstractToolbar):
    __slots__ = (
        'color_view', 'outputs', 'position', 'pos_fmt',
        'rgb_dec', 'rgb_hex', 'rgb_label',
        'src_dec', 'src_dec_fmt', 'src_hex', 'src_hex_fmt', 'src_label',
    )

    data_types = {
        vs.INTEGER: {
            1: ctypes.c_uint8,
            2: ctypes.c_uint16,
            # 4: ctypes.c_char * 4,
        },
        vs.FLOAT: {
            # 2: ctypes.c_char * 2,
            4: ctypes.c_float,
        }
    }

    def __init__(self, main: AbstractMainWindow) -> None:
        super().__init__(main, 'Pipette')

        self.setup_ui()
        self.main.graphics_view.mouseMoved.connect(self.mouse_moved)

        self.pos_fmt = '{},{}'
        self.src_hex_fmt = '{:2X}'
        self.src_max_val: Union[int, float] = 2**8 - 1
        self.src_dec_fmt = '{:3d}'
        self.src_norm_fmt = '{:0.5f}'
        self.outputs: Dict[Output, vs.VideoNode] = {}

        set_qobject_names(self)

    def setup_ui(self) -> None:
        layout = Qt.QHBoxLayout(self)
        layout.setObjectName('PipetteToolbar.setup_ui.layout')
        layout.setContentsMargins(0, 0, 0, 0)

        self.color_view = ColorView(self)
        self.color_view.setFixedSize(self.height() // 2 , self.height() // 2)
        layout.addWidget(self.color_view)

        font = Qt.QFont('Consolas', 9)
        font.setStyleHint(Qt.QFont.Monospace)

        self.position = Qt.QLabel(self)
        self.position.setFont(font)
        self.position.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.position)

        self.rgb_label = Qt.QLabel(self)
        self.rgb_label.setText('Rendered (RGB):')
        layout.addWidget(self.rgb_label)

        self.rgb_hex = Qt.QLabel(self)
        self.rgb_hex.setFont(font)
        self.rgb_hex.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.rgb_hex)

        self.rgb_dec = Qt.QLabel(self)
        self.rgb_dec.setFont(font)
        self.rgb_dec.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.rgb_dec)

        self.rgb_norm = Qt.QLabel(self)
        self.rgb_norm.setFont(font)
        self.rgb_norm.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.rgb_norm)

        self.src_label = Qt.QLabel(self)
        layout.addWidget(self.src_label)

        self.src_hex = Qt.QLabel(self)
        self.src_hex.setFont(font)
        self.src_hex.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.src_hex)

        self.src_dec = Qt.QLabel(self)
        self.src_dec.setFont(font)
        self.src_dec.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.src_dec)

        self.src_norm = Qt.QLabel(self)
        self.src_norm.setFont(font)
        self.src_norm.setTextInteractionFlags(Qt.Qt.TextSelectableByMouse)
        layout.addWidget(self.src_norm)

        layout.addStretch()

    def mouse_moved(self, event: Qt.QMouseEvent) -> None:
        if not event.buttons() & Qt.Qt.LeftButton:
            self.update_labels(event.pos())

    def update_labels(self, local_pos: Qt.QPoint) -> None:
        from math import floor, trunc
        from struct import unpack

        point_f = self.main.graphics_view.mapToScene(local_pos)
        point = Qt.QPoint(floor(point_f.x()), floor(point_f.y()))
        if not self.main.current_output.graphics_scene_item.contains(point_f):
            return
        color = self.main.current_output.graphics_scene_item.image() \
                    .pixelColor(point)
        self.color_view.color = color

        self.position.setText(self.pos_fmt.format(point.x(), point.y()))

        self.rgb_hex.setText('{:2X},{:2X},{:2X}'.format(
            color.red(), color.green(), color.blue()))
        self.rgb_dec.setText('{:3d},{:3d},{:3d}'.format(
            color.red(), color.green(), color.blue()))
        self.rgb_norm.setText('{:0.5f},{:0.5f},{:0.5f}'.format(
            color.red() / 255, color.green() / 255, color.blue() / 255))

        if not self.src_label.isVisible():
            return

        src_vals: List[Union[int, float]] = []
        vs_frame = self.outputs[self.main.current_output].get_frame(
            int(self.main.current_frame))
        fmt = vs_frame.format
        idx = point.y() * vs_frame.width + point.x()

        for i in range(vs_frame.format.num_planes):
            if fmt.sample_type == vs.FLOAT and fmt.bytes_per_sample == 2:
                ptr = ctypes.cast(vs_frame.get_read_ptr(i), ctypes.POINTER(
                    ctypes.c_char * (2 * vs_frame.width * vs_frame.height)))
                val = unpack('e', ptr.contents[(idx * 2):(idx * 2 + 2)])[0]  # type: ignore
                src_vals.append(val)
            else:
                ptr = ctypes.cast(vs_frame.get_read_ptr(i), ctypes.POINTER(
                    self.data_types[fmt.sample_type][fmt.bytes_per_sample] * (  # type:ignore
                        vs_frame.width * vs_frame.height)))
                src_vals.append(ptr.contents[idx])  # type: ignore

        self.src_dec.setText(self.src_dec_fmt.format(*src_vals))
        if fmt.sample_type == vs.INTEGER:
            self.src_hex.setText(self.src_hex_fmt.format(*src_vals))
            self.src_norm.setText(self.src_norm_fmt.format(
                *[src_val / self.src_max_val for src_val in src_vals]))
        elif fmt.sample_type == vs.FLOAT:
            self.src_norm.setText(self.src_norm_fmt.format(*[
                self.clip(val, 0.0, 1.0) if i == 0 else
                self.clip(val, -0.5, 0.5) + 0.5
                for i, val in enumerate(src_vals)
            ]))

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        from math import ceil, log

        def hide() -> None:
            self.src_label.setVisible(False)
            self.src_dec.setVisible(False)
            self.src_hex.setVisible(False)
            self.src_norm.setVisible(False)

        def show_and_reset() -> None:
            self.src_label.setVisible(True)
            self.src_dec.setVisible(True)
            self.src_hex.setVisible(True)
            self.src_norm.setVisible(True)
            self.src_label.setText('')
            self.src_hex.setText('')
            self.src_dec.setText('')
            self.src_norm.setText('')

        super().on_current_output_changed(index, prev_index)

        hide()
        fmt = self.main.current_output.format
        if fmt.color_family == vs.RGB:
            show_and_reset()
            self.src_label.setText('Raw (RGB):')
        elif fmt.color_family == vs.YUV:
            show_and_reset()
            self.src_label.setText('Raw (YUV):')
        elif fmt.color_family == vs.GRAY:
            show_and_reset()
            self.src_label.setText('Raw (Gray):')
        elif fmt.color_family == vs.YCOCG:
            show_and_reset()
            self.src_label.setText('Raw (YCoCg):')
        elif fmt.id == vs.COMPATBGR32.value:
            show_and_reset()
            self.src_label.setText('Raw (RGB)')
        elif fmt.id == vs.COMPATYUY2.value:
            show_and_reset()
            self.src_label.setText('Raw (YUV)')

        self.pos_fmt = '{{:{}d}},{{:{}d}}'.format(
            ceil(log(self.main.current_output.width, 10)),
            ceil(log(self.main.current_output.height, 10)))

        if self.main.current_output not in self.outputs:
            self.outputs[self.main.current_output] = self.prepare_vs_output(
                self.main.current_output.source_vs_output)
        src_fmt = self.outputs[self.main.current_output].format

        if src_fmt.sample_type == vs.INTEGER:
            self.src_max_val = 2**src_fmt.bits_per_sample - 1
        elif src_fmt.sample_type == vs.FLOAT:
            self.src_hex.setVisible(False)
            self.src_max_val = 1.0

        self.src_hex_fmt = ','.join(('{{:{w}X}}',) * src_fmt.num_planes) \
                           .format(w=ceil(log(self.src_max_val, 16)))
        if src_fmt.sample_type == vs.INTEGER:
            self.src_dec_fmt = ','.join(('{{:{w}d}}',) * src_fmt.num_planes) \
                               .format(w=ceil(log(self.src_max_val, 10)))
        elif src_fmt.sample_type == vs.FLOAT:
            self.src_dec_fmt = ','.join(('{: 0.5f}',) * src_fmt.num_planes)
        self.src_norm_fmt = ','.join(('{:0.5f}',) * src_fmt.num_planes)

        self.update_labels(self.main.graphics_view.mapFromGlobal(
            self.main.cursor().pos()))

    def on_toggle(self, new_state: bool) -> None:
        super().on_toggle(new_state)
        self.main.graphics_view.setMouseTracking(new_state)
        if new_state is True:
            self.main.graphics_view.setDragMode(Qt.QGraphicsView.NoDrag)
        else:
            self.main.graphics_view.setDragMode(
                Qt.QGraphicsView.ScrollHandDrag)

    @staticmethod
    def prepare_vs_output(vs_output: vs.VideoNode) -> vs.VideoNode:
        def non_subsampled_format(fmt: vs.Format) -> vs.Format:
            if fmt.id == vs.COMPATBGR32.value:
                return vs.RGB24  # type: ignore
            elif fmt.id == vs.COMPATYUY2.value:
                return vs.YUV444P8  # type: ignore
            else:
                return vs.core.register_format(
                    color_family=fmt.color_family,
                    sample_type=fmt.sample_type,
                    bits_per_sample=fmt.bits_per_sample,
                    subsampling_w=0,
                    subsampling_h=0
                )

        return vs.core.resize.Bicubic(
            vs_output,
            format=non_subsampled_format(vs_output.format))

    @staticmethod
    def clip(value: Number, lower_bound: Number, upper_bound: Number) -> Number:
        return max(lower_bound, min(value, upper_bound))
