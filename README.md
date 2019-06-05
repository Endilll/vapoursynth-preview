Standalone preview for VapourSynth scripts. Meant to be paired with a code editor with integrated terminal like Visual Studio Code.

# Prerequisites

Python 3.7.3

Vapoursynth R45

pip modules:

`cueparser psutil pyqt5 pysubs2 pyyaml qdarkstyle vapoursynth`

# Usage

`python run.py script.vpy` where `script.vpy` is path to VapourSynth script.

# Note

WIP, so there're some debug stuff among the logic, but not much.

# Development

pip modules:

`mypy pycodestyle pylint pyqt5-stubs`

PyQt5 stubs may be incomplete when it comes to signals.
