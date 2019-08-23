import logging
from   typing  import Any, Mapping

from yaml import YAMLObject

from vspreview.core import Output

DARK_THEME = True
LOG_LEVEL  = logging.DEBUG

VS_OUTPUT_RESIZER       = Output.Resizer.Bicubic
VS_OUTPUT_MATRIX        = Output.Matrix.BT709
VS_OUTPUT_TRANSFER      = Output.Transfer.BT709
VS_OUTPUT_PRIMARIES     = Output.Primaries.BT709
VS_OUTPUT_RANGE         = Output.Range.LIMITED
VS_OUTPUT_CHROMALOC     = Output.ChromaLoc.LEFT
VS_OUTPUT_PREFER_PROPS  = True
VS_OUTPUT_RESIZER_KWARGS: Mapping[str, str] = {}


class Settings(YAMLObject):
    yaml_tag = '!Settings'
    # pylint: disable=attribute-defined-outside-init

    def __init__(self) -> None:
        self.set_defaults()

    def set_defaults(self) -> None:
        self.dark_theme = True

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        self.set_defaults()

        try:
            dark_theme = state['dark theme']
            if not isinstance(dark_theme, bool):
                raise TypeError
            self.dark_theme = dark_theme
        except (KeyError, TypeError):
            logging.warning('Storage loading: PlaybackToolbar: failed to parse seek_interval_frame')
