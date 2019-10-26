from __future__ import annotations

import logging
import os
from   pathlib  import Path
import sys
from   typing   import Any, cast, Mapping, Optional, Union

from   PyQt5       import Qt
import vapoursynth as     vs

from vspreview.core import (
    AbstractMainWindow, AbstractToolbar, AbstractToolbars, Frame,
    FrameInterval, Output, Time, TimeInterval
)
from vspreview.models import Outputs
from vspreview.utils import (
    add_shortcut, debug, get_usable_cpus_count, qt_silent_call,
    set_qobject_names
)
from vspreview.widgets import (
    ComboBox, StatusBar, TimeEdit, Timeline, FrameEdit
)


# TODO: design settings
# TODO: deisgn keyboard layout
# TODO: VFR support
# TODO: move to pyside2, but it lacks single Qt namespace
#       with everything imported and it isn't type annotated.
#       See https://bugreports.qt.io/browse/PYSIDE-735
# TODO: get rid of magical constants related to 'pixel' sizes
#       (their actual units are yet to be discovered)
# TODO: move from QGraphicsView to QLabel
# TODO: utilize Qt's signals
# TODO: save window position
# TODO: make use of alpha channel of outputs
# TODO: respect cursor position when zooming in and out


class ScriptErrorDialog(Qt.QDialog):
    __slots__ = (
        'main', 'label', 'reload_button', 'exit_button'
    )

    def __init__(self, main_window: AbstractMainWindow) -> None:
        super().__init__(main_window, Qt.Qt.Dialog)
        self.main = main_window

        self.setWindowTitle('Script Loading Error')
        self.setModal(True)

        self.setup_ui()

        self.reload_button.clicked.connect(self.on_reload_clicked)
        self.exit_button  .clicked.connect(self.on_exit_clicked)

        add_shortcut(Qt.Qt.CTRL + Qt.Qt.Key_R, self.reload_button.click, self)

        set_qobject_names(self)

    def setup_ui(self) -> None:
        main_layout = Qt.QVBoxLayout(self)
        main_layout.setObjectName('ScriptErrorDialog.setup_ui.main_layout')

        self.label = Qt.QLabel()
        main_layout.addWidget(self.label)

        buttons_widget = Qt.QWidget(self)
        buttons_widget.setObjectName('ScriptErrorDialog.setup_ui.buttons_widget')
        buttons_layout = Qt.QHBoxLayout(buttons_widget)
        buttons_layout.setObjectName('ScriptErrorDialog.setup_uibuttons_layout')

        self.reload_button = Qt.QPushButton(self)
        self.reload_button.setText('Reload')
        buttons_layout.addWidget(self.reload_button)

        self.exit_button = Qt.QPushButton(self)
        self.exit_button.setText('Exit')
        buttons_layout.addWidget(self.exit_button)

        main_layout.addWidget(buttons_widget)

    def on_reload_clicked(self, clicked: Optional[bool] = None) -> None:
        self.hide()
        self.main.reload_script()

    def on_exit_clicked(self, clicked: Optional[bool] = None) -> None:
        self.hide()
        self.main.save_on_exit = False
        self.main.app.exit()

    def closeEvent(self, event: Qt.QCloseEvent) -> None:
        self.on_exit_clicked()


class MainToolbar(AbstractToolbar):
    __slots__ = (
        'outputs', 'save_file_types', 'zoom_levels',
        'outputs_combobox', 'frame_control', 'copy_frame_button',
        'time_control', 'copy_timestamp_button',
        'zoom_combobox', 'save_as_button', 'switch_timeline_mode_button',
    )

    def __init__(self, main_window: AbstractMainWindow) -> None:
        from vspreview.models import ZoomLevels

        super().__init__(main_window, 'Main')
        self.setup_ui()

        self.outputs = Outputs()

        self.outputs_combobox.setModel(self.outputs)
        self.zoom_levels = ZoomLevels([
            0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0
        ])
        self.zoom_combobox.setModel(self.zoom_levels)
        self.zoom_combobox.setCurrentIndex(3)

        self.save_file_types = {
            'Single Image (*.png)': self.save_as_png
        }

        self.outputs_combobox.currentIndexChanged.connect(self.main.switch_output)
        self.frame_control          .valueChanged.connect(self.main.switch_frame)
        self.time_control           .valueChanged.connect(self.main.switch_frame)
        self.frame_control       .editingFinished.connect(self.frame_control.clearFocus)
        self.time_control        .editingFinished.connect(self.time_control.clearFocus)
        self.copy_frame_button           .clicked.connect(self.on_copy_frame_button_clicked)
        self.copy_timestamp_button       .clicked.connect(self.on_copy_timestamp_button_clicked)
        self.sync_outputs_checkbox  .stateChanged.connect(self.on_sync_outputs_changed)
        self.zoom_combobox    .currentTextChanged.connect(self.on_zoom_changed)
        self.save_as_button              .clicked.connect(self.on_save_as_clicked)
        self.switch_timeline_mode_button .clicked.connect(self.on_switch_timeline_mode_clicked)

        add_shortcut(Qt.Qt.Key_1, lambda: self.main.switch_output(0))
        add_shortcut(Qt.Qt.Key_2, lambda: self.main.switch_output(1))
        add_shortcut(Qt.Qt.Key_3, lambda: self.main.switch_output(2))
        add_shortcut(Qt.Qt.Key_4, lambda: self.main.switch_output(3))
        add_shortcut(Qt.Qt.Key_5, lambda: self.main.switch_output(4))
        add_shortcut(Qt.Qt.Key_6, lambda: self.main.switch_output(5))
        add_shortcut(Qt.Qt.Key_7, lambda: self.main.switch_output(6))
        add_shortcut(Qt.Qt.Key_8, lambda: self.main.switch_output(7))
        add_shortcut(Qt.Qt.Key_9, lambda: self.main.switch_output(8))
        add_shortcut(Qt.Qt.Key_0, lambda: self.main.switch_output(9))
        add_shortcut(Qt.Qt.Key_S,         self.sync_outputs_checkbox.click)

        set_qobject_names(self)

    def setup_ui(self) -> None:
        self.setVisible(True)
        layout = Qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.outputs_combobox = ComboBox[Output](self)
        self.outputs_combobox.setEditable(True)
        self.outputs_combobox.setInsertPolicy(Qt.QComboBox.InsertAtCurrent)
        self.outputs_combobox.setDuplicatesEnabled(True)
        self.outputs_combobox.setSizeAdjustPolicy(Qt.QComboBox.AdjustToContents)
        layout.addWidget(self.outputs_combobox)

        self.frame_control = FrameEdit[Frame](self)
        self.frame_control.setKeyboardTracking(False)
        layout.addWidget(self.frame_control)

        self.copy_frame_button = Qt.QPushButton(self)
        self.copy_frame_button.setText('⎘')
        layout.addWidget(self.copy_frame_button)

        self.time_control = TimeEdit[Time](self)
        self.time_control.setKeyboardTracking(False)
        layout.addWidget(self.time_control)

        self.copy_timestamp_button = Qt.QPushButton(self)
        self.copy_timestamp_button.setText('⎘')
        layout.addWidget(self.copy_timestamp_button)

        self.sync_outputs_checkbox = Qt.QCheckBox(self)
        self.sync_outputs_checkbox.setText('Sync Outputs')
        layout.addWidget(self.sync_outputs_checkbox)

        self.zoom_combobox = ComboBox[float](self)
        self.zoom_combobox.setMinimumContentsLength(4)
        layout.addWidget(self.zoom_combobox)

        self.save_as_button = Qt.QPushButton(self)
        self.save_as_button.setText('Save Frame as')
        layout.addWidget(self.save_as_button)

        self.switch_timeline_mode_button = Qt.QPushButton(self)
        self.switch_timeline_mode_button.setText('Switch Timeline Mode')
        layout.addWidget(self.switch_timeline_mode_button)

        layout.addStretch()

        self.toggle_button.setVisible(False)

    def on_current_frame_changed(self, frame: Frame, time: Time) -> None:
        qt_silent_call(self.frame_control.setValue, frame)
        qt_silent_call(self. time_control.setValue,  time)

        if self.sync_outputs_checkbox.isChecked():
            for output in self.main.outputs:
                output.frame_to_show = frame

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        qt_silent_call(self.outputs_combobox.setCurrentIndex, index)
        qt_silent_call(self.   frame_control.setMaximum, self.main.current_output.end_frame)
        qt_silent_call(self.    time_control.setMaximum, self.main.current_output.end_time)


    def rescan_outputs(self) -> None:
        self.outputs = Outputs()
        self.main.init_outputs()
        self.outputs_combobox.setModel(self.outputs)

    def on_copy_frame_button_clicked(self, checked: Optional[bool] = None) -> None:
        self.main.clipboard.setText(str(self.main.current_frame))
        self.main.statusbar.showMessage('Current frame number copied to clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

    def on_copy_timestamp_button_clicked(self, checked: Optional[bool] = None) -> None:
        self.main.clipboard.setText(self.time_control.text())
        self.main.statusbar.showMessage('Current timestamp copied to clipboard', self.main.STATUSBAR_MESSAGE_TIMEOUT)

    def on_sync_outputs_changed(self, state: Qt.Qt.CheckState) -> None:
        if state == Qt.Qt.Checked:
            for output in self.main.outputs:
                output.frame_to_show = self.main.current_frame
        if state == Qt.Qt.Unchecked:
            for output in self.main.outputs:
                output.frame_to_show = None

    def on_switch_timeline_mode_clicked(self, checked: Optional[bool] = None) -> None:
        if self.main.timeline.mode == self.main.timeline.Mode.TIME:
            self.main.timeline.mode = self.main.timeline.Mode.FRAME
        elif self.main.timeline.mode == self.main.timeline.Mode.FRAME:
            self.main.timeline.mode = self.main.timeline.Mode.TIME

    def on_zoom_changed(self, text: Optional[str] = None) -> None:
        self.main.graphics_view.setZoom(self.zoom_combobox.currentData())

    def on_save_as_clicked(self, checked: Optional[bool] = None) -> None:
        filter_str = ''.join([file_type + ';;' for file_type in self.save_file_types.keys()])
        filter_str = filter_str[0:-2]

        template = self.main.toolbars.misc.save_template_lineedit.text()
        try:
            suggested_path_str = template.format(script_name=self.main.script_path.with_suffix(''), frame=self.main.current_frame)
        except ValueError:
            suggested_path_str = self.main.SAVE_TEMPLATE.format(script_name=self.main.script_path.with_suffix(''), frame=self.main.current_frame)
            self.main.statusbar.showMessage('Save name template is invalid', self.main.STATUSBAR_MESSAGE_TIMEOUT)

        save_path_str, file_type = Qt.QFileDialog.getSaveFileName(self.main, 'Save as', suggested_path_str, filter_str)
        try:
            self.save_file_types[file_type](Path(save_path_str))
        except KeyError:
            pass

    def save_as_png(self, path: Path) -> None:
        image = self.main.current_output.graphics_scene_item.pixmap().toImage()
        image.save(str(path), 'PNG', self.main.PNG_COMPRESSION_LEVEL)

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            'current_output_index': self.outputs_combobox.currentIndex(),
            'outputs'             : self.outputs
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            self.outputs = state['outputs']
            self.main.init_outputs()
            self.outputs_combobox.setModel(self.outputs)
        except KeyError:
            logging.warning('Storage loading: Main toolbar: failed to parse outputs.')

        try:
            self.main.switch_output(state['current_output_index'])
            if self.outputs_combobox.currentIndex() == -1:
                raise ValueError
        except (KeyError, TypeError):
            logging.warning('Storage loading: Main toolbar: failed to parse output index.')
            self.main.switch_output(self.main.OUTPUT_INDEX)
        except ValueError:
            logging.warning('Storage loading: Main toolbar: stored output index is not valid.')
            self.main.switch_output(self.main.OUTPUT_INDEX)


class Toolbars(AbstractToolbars):
    yaml_tag = '!Toolbars'

    def __init__(self, main_window: AbstractMainWindow) -> None:
        from vspreview.toolbars import (
            DebugToolbar, MiscToolbar, PlaybackToolbar, SceningToolbar,
            BenchmarkToolbar
        )

        self.main      =      MainToolbar(main_window)
        self.main.setObjectName('Toolbars.main')

        self.misc      =      MiscToolbar(main_window)
        self.playback  =  PlaybackToolbar(main_window)
        self.scening   =   SceningToolbar(main_window)
        self.benchmark = BenchmarkToolbar(main_window)
        self.debug     =     DebugToolbar(main_window)

        self.misc     .setObjectName('Toolbars.misc')
        self.playback .setObjectName('Toolbars.playback')
        self.scening  .setObjectName('Toolbars.scening')
        self.benchmark.setObjectName('Toolbars.benchmark')
        self.debug    .setObjectName('Toolbars.debug')


    def __getstate__(self) -> Mapping[str, Mapping[str, Any]]:
        return {
            toolbar_name: getattr(self, toolbar_name).__getstate__()
            for toolbar_name in self.all_toolbars_names
        }

    def __setstate__(self, state: Mapping[str, Mapping[str, Any]]) -> None:
        for toolbar_name in self.all_toolbars_names:
            try:
                storage = state[toolbar_name]
                if not isinstance(storage, Mapping):
                    raise TypeError
                getattr(self, toolbar_name).__setstate__(storage)
            except (KeyError, TypeError):
                logging.warning(f'Storage loading: failed to parse storage of {toolbar_name}.')


class MainWindow(AbstractMainWindow):
    # those are defaults that can be overriden at runtime or used as fallbacks
    AUTOSAVE_ENABLED          =  True
    AUTOSAVE_INTERVAL         =    30 * 1000  # s
    BASE_PPI                  =    96  # PPI
    BENCHMARK_CLEAR_CACHE     = False
    BENCHMARK_REFRESH_INTERVAL =  150  # ms
    DARK_THEME                =  True
    FPS_AVERAGING_WINDOW_SIZE = FrameInterval(100)
    FPS_REFRESH_INTERVAL      =   150  # ms
    LOG_LEVEL         = logging.DEBUG
    OPENGL_RENDERING          = False
    OUTPUT_INDEX              =     0
    PLAY_BUFFER_SIZE = FrameInterval(get_usable_cpus_count())
    PNG_COMPRESSION_LEVEL     =     0  # 0 - 100
    SAVE_TEMPLATE = '{script_name}_{frame}'
    SEEK_STEP                 =     1  # frames
    STATUSBAR_MESSAGE_TIMEOUT =     3 * 1000  # s
    # it's allowed to stretch target interval betweewn notches by 20% at most
    TIMELINE_LABEL_NOTCHES_MARGIN = 20  # %
    TIMELINE_MODE             = 'frame'
    # would be used for formats with subsampling
    VS_OUTPUT_RESIZER         = Output.Resizer.Bicubic
    VS_OUTPUT_MATRIX          = Output.Matrix.BT709
    VS_OUTPUT_TRANSFER        = Output.Transfer.BT709
    VS_OUTPUT_PRIMARIES       = Output.Primaries.BT709
    VS_OUTPUT_RANGE           = Output.Range.LIMITED
    VS_OUTPUT_CHROMALOC       = Output.ChromaLoc.LEFT
    VS_OUTPUT_PREFER_PROPS    = True
    VS_OUTPUT_RESIZER_KWARGS  = {}  # type: Mapping[str, str]

    BENCHMARK_FRAME_DATA_SHARING_FIX  =  True
    DEBUG_PLAY_FPS                    = False
    DEBUG_TOOLBAR                     = False
    DEBUG_TOOLBAR_BUTTONS_PRINT_STATE = False

    yaml_tag = '!MainWindow'

    storable_attrs = [
        'toolbars',
    ]
    __slots__ = storable_attrs + [
        'app', 'display_scale', 'clipboard',
        'script_path', 'save_on_exit', 'timeline', 'main_layout',
        'graphics_scene', 'graphics_view', 'script_error_dialog',
        'central_widget', 'statusbar',
        'opengl_widget',
    ]

    def __init__(self) -> None:
        from qdarkstyle import load_stylesheet_pyqt5

        super().__init__()

        # logging

        logging.basicConfig(format='{asctime}: {levelname}: {message}', style='{', level=self.LOG_LEVEL)
        logging.Formatter.default_msec_format = '%s.%03d'

        # ???

        self.app = Qt.QApplication.instance()
        if self.DARK_THEME:
            self.app.setStyleSheet(self.patch_dark_stylesheet(load_stylesheet_pyqt5()))
            self.ensurePolished()

        self.display_scale = self.app.primaryScreen().logicalDotsPerInch() / self.BASE_PPI
        self.setWindowTitle('VSPreview')
        self.move(400, 0)
        self.setup_ui()

        # global

        self.clipboard    = self.app.clipboard()
        self.script_path  = Path()
        self.save_on_exit = True

        # graphics view

        self.graphics_scene = Qt.QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.opengl_widget = None
        if self.OPENGL_RENDERING:
            self.opengl_widget = Qt.QOpenGLWidget()
            self.graphics_view.setViewport(self.opengl_widget)

        self.graphics_view.wheelScrolled.connect(self.on_wheel_scrolled)

        # timeline

        self.timeline.clicked.connect(self.switch_frame)

        # init toolbars and outputs

        self.toolbars = Toolbars(self)
        self.main_layout.addWidget(self.toolbars.main)
        for toolbar in self.toolbars:
            self.main_layout.addWidget(toolbar)
            self.toolbars.main.layout().addWidget(toolbar.toggle_button)

        set_qobject_names(self)

    def setup_ui(self) -> None:
        from vspreview.widgets import GraphicsView

        # mainWindow.resize(1300, 808)

        self.central_widget = Qt.QWidget(self)
        self.main_layout = Qt.QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        self.graphics_view = GraphicsView(self.central_widget)
        # self.graphics_view.setOptimizationFlag(Qt.QGraphicsView.DontSavePainterState)
        # self.graphics_view.setOptimizationFlag(Qt.QGraphicsView.DontAdjustForAntialiasing)
        # self.graphics_view.setViewportUpdateMode(Qt.QGraphicsView.FullViewportUpdate)
        self.graphics_view.setBackgroundBrush(self.palette().brush(Qt.QPalette.Window))
        self.graphics_view.setSizePolicy(Qt.QSizePolicy.Fixed, Qt.QSizePolicy.Fixed)
        self.graphics_view.setDragMode(Qt.QGraphicsView.ScrollHandDrag)
        self.graphics_view.setTransformationAnchor(GraphicsView.AnchorUnderMouse)
        self.main_layout.addWidget(self.graphics_view)

        self.timeline = Timeline(self.central_widget)
        self.main_layout.addWidget(self.timeline)

        # status bar

        self.statusbar = StatusBar(self.central_widget)

        self.statusbar.total_frames_label = Qt.QLabel(self.central_widget)
        self.statusbar.total_frames_label.setObjectName('MainWindow.statusbar.total_frames_label')
        self.statusbar.addWidget(self.statusbar.total_frames_label)

        self.statusbar.duration_label = Qt.QLabel(self.central_widget)
        self.statusbar.duration_label.setObjectName('MainWindow.statusbar.duration_label')
        self.statusbar.addWidget(self.statusbar.duration_label)

        self.statusbar.resolution_label = Qt.QLabel(self.central_widget)
        self.statusbar.resolution_label.setObjectName('MainWindow.statusbar.resolution_label')
        self.statusbar.addWidget(self.statusbar.resolution_label)

        self.statusbar.pixel_format_label = Qt.QLabel(self.central_widget)
        self.statusbar.pixel_format_label.setObjectName('MainWindow.statusbar.pixel_format_label')
        self.statusbar.addWidget(self.statusbar.pixel_format_label)

        self.statusbar.fps_label = Qt.QLabel(self.central_widget)
        self.statusbar.fps_label.setObjectName('MainWindow.statusbar.fps_label')
        self.statusbar.addWidget(self.statusbar.fps_label)

        self.statusbar.label = Qt.QLabel(self.central_widget)
        self.statusbar.label.setObjectName('MainWindow.statusbar.label')
        self.statusbar.addPermanentWidget(self.statusbar.label)

        self.setStatusBar(self.statusbar)

        # dialogs

        self.script_error_dialog = ScriptErrorDialog(self)

    def patch_dark_stylesheet(self, stylesheet: str) -> str:
        return stylesheet + 'QGraphicsView { border: 0px; padding: 0px; }'

    def load_script(self, script_path: Path) -> None:
        from traceback import print_exc

        self.toolbars.playback.stop()

        self.statusbar.label.setText('Evaluating')
        self.script_path = script_path
        sys.path.append(str(self.script_path.parent))
        try:
            exec(self.script_path.read_text(), {})  # pylint: disable=exec-used
        except Exception:  # pylint: disable=broad-except
            logging.error('Script contains error(s). Check following lines for details.')
            self.handle_script_error('Script contains error(s). See console output for details.')
            print_exc()
            return
        finally:
            sys.path.pop()

        if len(vs.get_outputs()) == 0:
            logging.error('Script has no outputs set.')
            self.handle_script_error('Script has no outputs set.')
            return

        self.toolbars.main.rescan_outputs()
        # self.init_outputs()
        self.switch_output(self.OUTPUT_INDEX)

        self.load_storage()

    def load_storage(self) -> None:
        import yaml

        storage_path = self.script_path.with_suffix('.yml')
        if storage_path.exists():
            try:
                yaml.load(storage_path.open(), Loader=yaml.Loader)
            except yaml.YAMLError as exc:
                if isinstance(exc, yaml.MarkedYAMLError):
                    logging.warning('Storage parsing failed on line {} column {}. Using defaults.'
                                    .format(exc.problem_mark.line + 1, exc.problem_mark.column + 1))  # pylint: disable=no-member
                else:
                    logging.warning('Storage parsing failed. Using defaults.')
        else:
            logging.info('No storage found. Using defaults.')

        self.statusbar.label.setText('Ready')

    def init_outputs(self) -> None:
        self.graphics_scene.clear()
        for output in self.outputs:
            frame_pixmap = output.render_frame(output.last_showed_frame)
            frame_item   = self.graphics_scene.addPixmap(frame_pixmap)
            frame_item.hide()
            output.graphics_scene_item = frame_item

    def reload_script(self) -> None:
        if self.toolbars.misc.autosave_enabled:
            self.toolbars.misc.save()
        vs.clear_outputs()
        self.graphics_scene.clear()
        self.load_script(self.script_path)

        self.statusbar.showMessage('Reloaded successfully', self.STATUSBAR_MESSAGE_TIMEOUT)

    def render_frame(self, frame: Frame, output: Optional[Output] = None) -> Qt.QPixmap:
        return self.current_output.render_frame(frame)

    def switch_frame(self, frame: Optional[Frame] = None, time: Optional[Time] = None, *, render_frame: bool = True) -> None:
        if frame is not None:
            time = Time(frame)
        elif time is not None:
            frame = Frame(time)
        else:
            logging.debug('switch_frame(): both frame and time is None')
            return
        if frame > self.current_output.end_frame:
            # logging.debug('switch_frame(): New frame position is out of range')
            return

        self.current_output.last_showed_frame = frame

        self.timeline.set_position(frame)
        self.toolbars.main.on_current_frame_changed(frame, time)
        for toolbar in self.toolbars:
            toolbar.on_current_frame_changed(frame, time)

        if render_frame:
            self.current_output.graphics_scene_item.setPixmap(self.render_frame(frame))

    def switch_output(self, value: Union[int, Output]) -> None:
        if len(self.outputs) == 0:
            # TODO: consider returning False
            return
        if isinstance(value, Output):
            index = self.outputs.index_of(value)
        else:
            index = value

        if index < 0 or index >= len(self.outputs):
            return

        prev_index = self.toolbars.main.outputs_combobox.currentIndex()

        self.toolbars.playback.stop()

        # current_output relies on outputs_combobox
        self.toolbars.main.on_current_output_changed(index, prev_index)
        self.timeline.set_end_frame(self.current_output.end_frame)
        if self.current_output.frame_to_show is not None:
            self.current_frame = self.current_output.frame_to_show
        else:
            self.current_frame = self.current_output.last_showed_frame

        for output in self.outputs:
            output.graphics_scene_item.hide()
        self.current_output.graphics_scene_item.show()
        self.graphics_scene.setSceneRect(Qt.QRectF(self.current_output.graphics_scene_item.pixmap().rect()))
        self.timeline.update_notches()
        for toolbar in self.toolbars:
            toolbar.on_current_output_changed(index, prev_index)
        self.update_statusbar_output_info()

    @property  # type: ignore
    def current_output(self) -> Output:  # type: ignore
        output = cast(Output, self.toolbars.main.outputs_combobox.currentData())
        # check currentData() return on empty combobox
        # if data != '':
        #    return cast(Output, data)
        # return None
        return output

    @current_output.setter
    def current_output(self, value: Output) -> None:
        self.switch_output(self.outputs.index_of(value))

    @property  # type: ignore
    def current_frame(self) -> Frame:  # type: ignore
        # if self.current_output is None:
        #     return None
        return self.current_output.last_showed_frame

    @current_frame.setter
    def current_frame(self, value: Frame) -> None:
        self.switch_frame(value)

    @property
    def outputs(self) -> Outputs:  # type: ignore
        return cast(Outputs, self.toolbars.main.outputs)


    def handle_script_error(self, message: str) -> None:
        # logging.error(message)
        self.script_error_dialog.label.setText(message)
        self.script_error_dialog.open()

    def on_wheel_scrolled(self, steps: int) -> None:
        new_index = self.toolbars.main.zoom_combobox.currentIndex() + steps
        if new_index < 0:
            new_index = 0
        elif new_index >= len(self.toolbars.main.zoom_levels):
            new_index = len(self.toolbars.main.zoom_levels) - 1
        self.toolbars.main.zoom_combobox.setCurrentIndex(new_index)

    def update_statusbar_output_info(self, output: Optional[Output] = None) -> None:
        if output is None:
            output = self.current_output

        self.statusbar.total_frames_label.setText('{} frames '.format(output.total_frames))
        self.    statusbar.duration_label.setText('{} '       .format(output.total_time))
        self.  statusbar.resolution_label.setText('{}x{} '    .format(output.width, output.height))
        self.statusbar.pixel_format_label.setText('{} '       .format(output.format.name))
        if output.fps_den != 0:
            self.statusbar.fps_label.setText('{}/{} = {:.3f} fps '.format(output.fps_num, output.fps_den, output.fps_num / output.fps_den))
        else:
            self.statusbar.fps_label.setText('{}/{} fps '         .format(output.fps_num, output.fps_den))

    def event(self, event: Qt.QEvent) -> bool:
        if event.type() == Qt.QEvent.LayoutRequest:
            self.timeline.full_repaint()

        return super().event(event)

    # misc methods

    def showEvent(self, event: Qt.QShowEvent) -> None:
        super().showEvent(event)
        self.graphics_view.setSizePolicy(Qt.QSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding))

    def closeEvent(self, event: Qt.QCloseEvent) -> None:
        if (self.toolbars.misc.autosave_enabled
                and self.save_on_exit):
            self.toolbars.misc.save()

    def __getstate__(self) -> Mapping[str, Any]:
        state = {
            attr_name: getattr(self, attr_name)
            for attr_name in self.storable_attrs
        }
        state.update({
            'timeline_mode': self.timeline.mode
        })
        return state

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        # toolbars is singleton, so it initialize itself right in its __setstate__()

        try:
            timeline_mode = state['timeline_mode']
            if not Timeline.Mode.is_valid(timeline_mode):
                raise TypeError
        except (KeyError, TypeError):
            logging.warning('Storage loading: failed to parse timeline mode. Using default.')
            timeline_mode = self.TIMELINE_MODE
        self.timeline.mode = timeline_mode


class Application(Qt.QApplication):
    def notify(self, obj: Qt.QObject, event: Qt.QEvent) -> bool:
        isex = False
        try:
            return Qt.QApplication.notify(self, obj, event)
        except Exception:  # pylint: disable=broad-except
            isex = True
            logging.error('Application: unexpected error')
            print(*sys.exc_info())
            return False
        finally:
            if isex:
                self.quit()


def main() -> None:
    from argparse import ArgumentParser

    check_versions()

    parser = ArgumentParser()
    parser.add_argument('script_path', help='Path to Vapoursynth script', type=Path, nargs='?')
    args = parser.parse_args()

    if args.script_path is None:
        print('Script path required.')
        sys.exit(1)

    script_path = args.script_path.resolve()
    if not script_path.exists():
        print('Script path is invalid.')
        sys.exit(1)

    # Qt.QApplication.setAttribute(Qt.Qt.AA_DisableHighDpiScaling)
    os.chdir(script_path.parent)
    app = Application(sys.argv)
    main_window = MainWindow()
    main_window.load_script(script_path)
    main_window.show()

    try:
        app.exec_()
    except Exception:  # pylint: disable=broad-except
        logging.error('app.exec_() exception')


def check_versions() -> bool:
    from pkg_resources import get_distribution
    from platform import python_version

    if sys.version_info < (3, 7, 3, 'final', 0):
        print('VSPreview is not tested on Python versions prior to 3.7.3 final, but you have {} {}. Use at your own risk.'.format(
            python_version(), sys.version_info.releaselevel))
        return False

    if get_distribution('PyQt5').version < '5.12':
        print('VSPreview is not tested on PyQt5 versions prior to 5.12, but you have {}. Use at your own risk.'.format(get_distribution('PyQt5').version))
        return False

    if vs.core.version_number() < 45:
        print('VSPreview is not tested on VapourSynth versions prior to 45, but you have {}. Use at your own risk.'.format(vs.core.version_number()))
        return False

    return True


if __name__ == '__main__':
    main()
