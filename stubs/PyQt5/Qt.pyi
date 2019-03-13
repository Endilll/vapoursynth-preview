# Providing our own module to existing stubs package feels like a hack,
# so I won't be surprised if it'll break after some CPython or Mypy update.

# pylint: skip-file

from .QtCore import *
from .QtDBus import *
from .QtGui import * # type: ignore
from .QtNetwork import *
from .QtOpenGL import *
from .QtPrintSupport import *
from .QtSql import *
from .QtTest import *
from .QtWidgets import *
from .QtXml import *
