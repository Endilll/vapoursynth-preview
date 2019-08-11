import logging
from   typing  import Mapping

from vspreview.core import Output

DARK_THEME = True
LOG_LEVEL = logging.DEBUG

VS_OUTPUT_RESIZER         = Output.Resizer.Bicubic
VS_OUTPUT_MATRIX          = Output.Matrix.BT709
VS_OUTPUT_TRANSFER        = Output.Transfer.BT709
VS_OUTPUT_PRIMARIES       = Output.Primaries.BT709
VS_OUTPUT_RANGE           = Output.Range.LIMITED
VS_OUTPUT_CHROMALOC       = Output.ChromaLoc.LEFT
VS_OUTPUT_PREFER_PROPS    = True
VS_OUTPUT_RESIZER_KWARGS: Mapping[str, str] = {}
