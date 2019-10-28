from __future__ import annotations

import logging
from   pathlib  import Path
from   typing   import Any, Mapping, Optional

from PyQt5 import Qt

from vspreview.core  import AbstractMainWindow, AbstractToolbar, Frame
from vspreview.utils import (
    add_shortcut, debug, fire_and_forget, set_qobject_names, set_status_label
)


class MiscToolbar(AbstractToolbar):
    storable_attrs = [
        'autosave_enabled',
    ]
    __slots__ = storable_attrs + [
        'autosave_timer', 'reload_script_button',
        'save_button', 'autosave_checkbox',
        'keep_on_top_checkbox', 'save_template_lineedit',
        'show_debug_checkbox',
        'toggle_button'
    ]

    def __init__(self, main: AbstractMainWindow) -> None:
        super().__init__(main, 'Misc')
        self.setup_ui()

        self.save_template_lineedit.setText(self.main.SAVE_TEMPLATE)

        self.autosave_enabled: bool = self.main.AUTOSAVE_ENABLED
        self.autosave_timer = Qt.QTimer()
        self.autosave_timer.timeout.connect(self.save)

        self.reload_script_button.     clicked.connect(lambda: self.main.reload_script())  # pylint: disable=unnecessary-lambda
        self.         save_button.     clicked.connect(lambda: self.save(manually=True))
        self.   autosave_checkbox.stateChanged.connect(        self.on_autosave_changed)
        self.keep_on_top_checkbox.stateChanged.connect(        self.on_keep_on_top_changed)
        self. show_debug_checkbox.stateChanged.connect(        self.on_show_debug_changed)

        add_shortcut(Qt.Qt.CTRL + Qt.Qt.Key_R, self.reload_script_button.click)
        add_shortcut(Qt.Qt.CTRL + Qt.Qt.Key_S, self.         save_button.click)

        set_qobject_names(self)

    def setup_ui(self) -> None:
        layout = Qt.QHBoxLayout(self)
        layout.setObjectName('MiscToolbar.setup_ui.layout')
        layout.setContentsMargins(0, 0, 0, 0)

        self.reload_script_button = Qt.QPushButton(self)
        self.reload_script_button.setText('Reload Script')
        layout.addWidget(self.reload_script_button)

        self.save_button = Qt.QPushButton(self)
        self.save_button.setText('Save')
        layout.addWidget(self.save_button)

        self.autosave_checkbox = Qt.QCheckBox(self)
        self.autosave_checkbox.setText('Autosave')
        layout.addWidget(self.autosave_checkbox)

        self.keep_on_top_checkbox = Qt.QCheckBox(self)
        self.keep_on_top_checkbox.setText('Keep on Top')
        self.keep_on_top_checkbox.setEnabled(False)
        layout.addWidget(self.keep_on_top_checkbox)

        save_template_label = Qt.QLabel(self)
        save_template_label.setObjectName(
            'MiscToolbar.setup_ui.save_template_label')
        save_template_label.setText('Save file name template:')
        layout.addWidget(save_template_label)

        self.save_template_lineedit = Qt.QLineEdit(self)
        self.save_template_lineedit.setToolTip(
            r'Use {script_name} and {frame} as placeholders.'
        )
        layout.addWidget(self.save_template_lineedit)

        layout.addStretch()
        layout.addStretch()

        self.show_debug_checkbox = Qt.QCheckBox(self)
        self.show_debug_checkbox.setText('Show Debug Toolbar')
        layout.addWidget(self.show_debug_checkbox)


    @fire_and_forget
    @set_status_label(label='Saving')
    def save(self, path: Optional[Path] = None, manually: bool = False) -> None:
        import yaml

        yaml.Dumper.ignore_aliases = lambda *args: True

        if path is None:
            path = self.main.script_path.with_suffix('.yml')

        with path.open(mode='w', newline='\n') as f:
            f.write(f'# VSPreview storage for {self.main.script_path}\n')
            yaml.dump(self.main, f, indent=4, default_flow_style=False)
        if manually:
            # timeout triggers QTimer creation, so we need this to be invoked in GUI thread
            # TODO: check if invokeMethod is still necessary
            Qt.QMetaObject.invokeMethod(
                self.main, 'show_message',  Qt.Qt.QueuedConnection,
                Qt.Q_ARG(str, 'Saved successfully')
            )

    def on_autosave_changed(self, state: Qt.Qt.CheckState) -> None:
        if   state == Qt.Qt.Checked:
            self.autosave_enabled = True
            self.autosave_timer.start(self.main.AUTOSAVE_INTERVAL)
        elif state == Qt.Qt.Unchecked:
            self.autosave_enabled = False
            self.autosave_timer.stop()

    def on_keep_on_top_changed(self, state: Qt.Qt.CheckState) -> None:
        if   state == Qt.Qt.Checked:
            pass
            # self.main.setWindowFlag(Qt.Qt.X11BypassWindowManagerHint)
            # self.main.setWindowFlag(Qt.Qt.WindowStaysOnTopHint, True)
        elif state == Qt.Qt.Unchecked:
            self.main.setWindowFlag(Qt.Qt.WindowStaysOnTopHint, False)

    def on_show_debug_changed(self, state: Qt.Qt.CheckState) -> None:
        if   state == Qt.Qt.Checked:
            self.main.toolbars.debug.toggle_button.setVisible(True)
        elif state == Qt.Qt.Unchecked:
            if self.main.toolbars.debug.toggle_button.isChecked():
                self.main.toolbars.debug.toggle_button.click()
            self.main.toolbars.debug.toggle_button.setVisible(False)

    def __getstate__(self) -> Mapping[str, Any]:
        state = {
            attr_name: getattr(self, attr_name)
            for attr_name in self.storable_attrs
        }
        state.update({
            'save_file_name_template': self.save_template_lineedit.text(),
            'show_debug'             : self.show_debug_checkbox.isChecked()
        })
        return state

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        try:
            autosave_enabled = state['autosave_enabled']
            if not isinstance(autosave_enabled, bool):
                raise TypeError
        except (KeyError, TypeError):
            logging.warning('Storage loading: failed to parse autosave flag.')
            autosave_enabled = self.main.AUTOSAVE_ENABLED

        self.autosave_checkbox.setChecked(autosave_enabled)

        try:
            self.save_template_lineedit.setText(state['save_file_name_template'])
        except (KeyError, TypeError):
            logging.warning('Storage loading: failed to parse save file name template.')

        try:
            show_debug = state['show_debug']
            if not isinstance(show_debug, bool):
                raise TypeError
        except (KeyError, TypeError):
            logging.warning('Storage loading: failed to parse show debug flag.')
            show_debug = self.main.DEBUG_TOOLBAR

        self.show_debug_checkbox.setChecked(show_debug)
