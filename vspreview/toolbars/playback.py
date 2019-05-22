from __future__ import annotations

from   datetime import timedelta
import logging
from   time     import perf_counter_ns
from   typing   import Any, Deque, Mapping, Optional, Union

from PyQt5 import Qt

from vspreview.core  import AbstractMainWindow, AbstractToolbar, Frame, FrameInterval
from vspreview.utils import add_shortcut, debug, qt_silent_call, qtime_to_timedelta, set_qobject_names, timedelta_to_qtime


class PlaybackToolbar(AbstractToolbar):
    __slots__ = (
        'play_timer', 'fps_timer', 'fps_history', 'current_fps',
        'seek_n_frames_b_button', 'seek_to_prev_button', 'play_pause_button',
        'seek_to_next_button', 'seek_n_frames_f_button',
        'seek_frame_spinbox', 'seek_time_spinbox',
        'fps_spinbox', 'fps_unlimited_checkbox', 'fps_reset_button',
        'play_buffer', 'toggle_button',
    )

    yaml_tag = '!PlaybackToolbar'

    def __init__(self, main_window: AbstractMainWindow) -> None:
        from collections        import deque
        from concurrent.futures import Future

        super().__init__(main_window)
        self.setup_ui()

        self.play_buffer: Deque[Future] = deque()
        self.play_timer = Qt.QTimer()
        self.play_timer.setTimerType(Qt.Qt.PreciseTimer)
        self.play_timer.timeout.connect(self._playback_show_next_frame)

        self.seek_frame_spinbox.setMinimum(int(FrameInterval(0)))
        self.seek_time_spinbox .setMinimumTime(Qt.QTime(0, 0))

        self.fps_history: Deque[int] = deque([], self.main.FPS_AVERAGING_WINDOW_SIZE)
        self.current_fps = 0.0
        self.fps_timer = Qt.QTimer()
        self.fps_timer.setTimerType(Qt.Qt.PreciseTimer)
        self.fps_timer.timeout.connect(lambda: self.fps_spinbox.setValue(self.current_fps))

        self.toggle_button              .clicked.connect(self.on_toggle)
        self.play_pause_button          .clicked.connect(self.on_play_pause_clicked)
        self.seek_to_prev_button        .clicked.connect(self.seek_to_prev)
        self.seek_to_next_button        .clicked.connect(self.seek_to_next)
        self.seek_n_frames_b_button     .clicked.connect(self.seek_n_frames_b)
        self.seek_n_frames_f_button     .clicked.connect(self.seek_n_frames_f)
        self.seek_frame_spinbox    .valueChanged.connect(self.on_seek_frame_changed)
        self.seek_time_spinbox      .timeChanged.connect(self.on_seek_time_changed)  # type: ignore
        self.fps_spinbox           .valueChanged.connect(self.on_fps_changed)
        self.fps_reset_button           .clicked.connect(self.reset_fps)
        self.fps_unlimited_checkbox.stateChanged.connect(self.on_fps_unlimited_changed)

        add_shortcut(              Qt.Qt.Key_Space, self.play_pause_button     .click)
        add_shortcut(              Qt.Qt.Key_Left , self.seek_to_prev_button   .click)
        add_shortcut(              Qt.Qt.Key_Right, self.seek_to_next_button   .click)
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_Left , self.seek_n_frames_b_button.click)
        add_shortcut(Qt.Qt.SHIFT + Qt.Qt.Key_Right, self.seek_n_frames_f_button.click)

        set_qobject_names(self)

    def setup_ui(self) -> None:
        self.setVisible(False)
        layout = Qt.QHBoxLayout(self)
        layout.setObjectName('PlaybackToolbar.setup_ui.layout')
        layout.setContentsMargins(0, 0, 0, 0)

        self.seek_n_frames_b_button = Qt.QPushButton(self)
        self.seek_n_frames_b_button.setText('⏮')
        self.seek_n_frames_b_button.setToolTip('Seek N Frames Backwards')
        layout.addWidget(self.seek_n_frames_b_button)

        self.seek_to_prev_button = Qt.QPushButton(self)
        self.seek_to_prev_button.setText('⏪')
        self.seek_to_prev_button.setToolTip('Seek 1 Frame Backwards')
        layout.addWidget(self.seek_to_prev_button)

        self.play_pause_button = Qt.QPushButton(self)
        self.play_pause_button.setText('⏯')
        self.play_pause_button.setToolTip('Play/Pause')
        self.play_pause_button.setCheckable(True)
        layout.addWidget(self.play_pause_button)

        self.seek_to_next_button = Qt.QPushButton(self)
        self.seek_to_next_button.setText('⏩')
        self.seek_to_next_button.setToolTip('Seek 1 Frame Forward')
        layout.addWidget(self.seek_to_next_button)

        self.seek_n_frames_f_button = Qt.QPushButton(self)
        self.seek_n_frames_f_button.setText('⏭')
        self.seek_n_frames_f_button.setToolTip('Seek N Frames Forward')
        layout.addWidget(self.seek_n_frames_f_button)

        self.seek_frame_spinbox = Qt.QSpinBox(self)
        self.seek_frame_spinbox.setMinimum(1)
        self.seek_frame_spinbox.setToolTip('Seek N Frames Step')
        layout.addWidget(self.seek_frame_spinbox)

        self.seek_time_spinbox = Qt.QTimeEdit(self)
        self.seek_time_spinbox.setDisplayFormat('H:mm:ss.zzz')
        self.seek_time_spinbox.setButtonSymbols(Qt.QTimeEdit.NoButtons)
        layout.addWidget(self.seek_time_spinbox)

        self.fps_spinbox = Qt.QDoubleSpinBox(self)
        self.fps_spinbox.setRange(1.0, 9999.0)
        self.fps_spinbox.setDecimals(3)
        self.fps_spinbox.setSuffix(' fps')
        layout.addWidget(self.fps_spinbox)

        self.fps_reset_button = Qt.QPushButton(self)
        self.fps_reset_button.setText('Reset FPS')
        layout.addWidget(self.fps_reset_button)

        self.fps_unlimited_checkbox = Qt.QCheckBox(self)
        self.fps_unlimited_checkbox.setText('Unlimited FPS')
        layout.addWidget(self.fps_unlimited_checkbox)

        layout.addStretch()

        # switch button for main toolbar

        self.toggle_button.setText('Playback')

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        qt_silent_call(self.seek_frame_spinbox.setMaximum    ,                    self.main.current_output.total_frames - FrameInterval(1))
        qt_silent_call(self. seek_time_spinbox.setMaximumTime, timedelta_to_qtime(self.main.current_output.duration))
        qt_silent_call(self.       fps_spinbox.setValue      ,                    self.main.current_output.play_fps)


    def play(self) -> None:
        if self.main.current_frame == self.main.current_output.total_frames - FrameInterval(1):
            return

        if self.main.statusbar.label.text() == 'Ready':
            self.main.statusbar.label.setText('Playing')

        self.play_buffer.clear()
        for i in range(self.main.PLAY_BUFFER_SIZE):
            future = self.main.current_output.vs_output.get_frame_async(int(self.main.current_frame + FrameInterval(i) + FrameInterval(1)))
            self.play_buffer.appendleft(future)

        if self.fps_unlimited_checkbox.isChecked():
            self.play_timer.start(0)
            self.fps_timer.start(self.main.FPS_REFRESH_INTERVAL)
        else:
            self.play_timer.start(round(1000 / self.main.current_output.play_fps))

    def _playback_show_next_frame(self) -> None:
        try:
            frame_future = self.play_buffer.pop()
        except IndexError:
            self.play_pause_button.click()
            return

        self.main.on_current_frame_changed(self.main.current_frame + FrameInterval(1), render_frame=False)
        pixmap = self.main.render_raw_videoframe(frame_future.result())
        self.main.current_output.graphics_scene_item.setPixmap(pixmap)

        self.update_fps_counter()

        next_frame_for_buffer = self.main.current_frame + self.main.PLAY_BUFFER_SIZE
        if next_frame_for_buffer < self.main.current_output.total_frames:
            self.play_buffer.appendleft(self.main.current_output.vs_output.get_frame_async(next_frame_for_buffer))

    def stop(self) -> None:
        self.play_timer.stop()
        if self.main.statusbar.label.text() == 'Playing':
            self.main.statusbar.label.setText('Ready')

        self.fps_history.clear()
        self.fps_timer.stop()

    def seek_to_prev(self, checked: Optional[bool] = None) -> None:
        try:
            new_pos = self.main.current_frame - FrameInterval(1)
        except ValueError:
            return
        self.stop()
        self.main.current_frame = new_pos

    def seek_to_next(self, checked: Optional[bool] = None) -> None:
        new_pos = self.main.current_frame + FrameInterval(1)
        if new_pos >= self.main.current_output.total_frames:
            return
        self.stop()
        self.main.current_frame = new_pos

    def seek_n_frames_b(self, checked: Optional[bool] = None) -> None:
        try:
            new_pos = self.main.current_frame - FrameInterval(self.seek_frame_spinbox.value())
        except ValueError:
            return
        self.stop()
        self.main.current_frame = new_pos

    def seek_n_frames_f(self, checked: Optional[bool] = None) -> None:
        new_pos = self.main.current_frame + FrameInterval(self.seek_frame_spinbox.value())
        if new_pos >= self.main.current_output.total_frames:
            return
        self.stop()
        self.main.current_frame = new_pos

    def on_seek_frame_changed(self, frame: Union[Frame, int]) -> None:
        frame = Frame(frame)
        qt_silent_call(self.seek_time_spinbox.setTime, timedelta_to_qtime(self.main.to_timedelta(frame)))

    def on_seek_time_changed(self, qtime: Qt.QTime) -> None:
        qt_silent_call(self.seek_frame_spinbox.setValue, self.main.to_frame(qtime_to_timedelta(qtime)))

    def on_play_pause_clicked(self, checked: bool) -> None:
        if checked:
            self.play()
        else:
            self.stop()

    def on_fps_changed(self, new_fps: float) -> None:
        if not self.fps_spinbox.isEnabled():
            return

        self.main.current_output.play_fps = new_fps
        if self.play_timer.isActive():
            self.stop()
            self.play()

    def reset_fps(self, checked: Optional[bool] = None) -> None:
        self.fps_spinbox.setValue(self.main.current_output.fps_num / self.main.current_output.fps_den)

    def on_fps_unlimited_changed(self, state: int) -> None:
        if state == Qt.Qt.Checked:
            self.fps_spinbox.setEnabled(False)
            self.fps_reset_button.setEnabled(False)
        if state == Qt.Qt.Unchecked:
            self.fps_spinbox.setEnabled(True)
            self.fps_reset_button.setEnabled(True)
            self.fps_spinbox.setValue(self.main.current_output.play_fps)

        if self.play_timer.isActive():
            self.stop()
            self.play()

    def update_fps_counter(self) -> None:
        if self.fps_spinbox.isEnabled():
            return

        self.fps_history.append(perf_counter_ns())
        if len(self.fps_history) == 1:
            return

        elapsed_total = 0
        for i in range(len(self.fps_history) - 1):
            elapsed_total += self.fps_history[i + 1] - self.fps_history[i]

        self.current_fps = 1_000_000_000 / (elapsed_total / len(self.fps_history))

    def __getstate__(self) -> Mapping[str, Any]:
        return {
            'seek_interval_frame': self.seek_frame_spinbox.value()
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            seek_interval_frame = state['seek_interval_frame']
            if not isinstance(seek_interval_frame, int):
                raise TypeError()
            self.seek_frame_spinbox.setValue(seek_interval_frame)
        except (KeyError, TypeError):
            logging.warning('Storage loading: PlaybackToolbar: failed to parse seek_interval_frame')
