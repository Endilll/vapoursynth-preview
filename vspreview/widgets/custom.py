from __future__ import annotations

from   datetime import timedelta
import logging
from   typing   import (
    Any, cast, Dict, Generic, Optional, Type, TYPE_CHECKING, TypeVar, Union,
)

from PyQt5 import Qt

from vspreview.core import (
    Frame, FrameInterval, FrameType, Time, TimeInterval, TimeType, Output,
)
from vspreview.models import SceningList
from vspreview.utils  import debug, from_qtime, to_qtime





