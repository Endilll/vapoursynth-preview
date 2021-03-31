Standalone preview for VapourSynth scripts. Meant to be paired with a code editor with integrated terminal like Visual Studio Code.

Feel free to contact me in [Telegram chat](https://t.me/vspreview_chat). Any feedback is appreciated.

# Prerequisites

* Python 3.8
* Vapoursynth R49
* pip modules in `requirements.txt`

You can use the following command to install pip modules:

`pip install -r requirements.txt`

# Usage

Assuming `script.vpy` is your VapourSynth script, there are two ways to run vspreview:
 * `python run.py script.vpy`
 * Add this directory (repository root) to your *PYTHONPATH*, and `python -m vspreview script.vpy`

# Note

WIP, so there're some debug stuff among the logic, but not much.

# Development

pip modules:

`mypy pycodestyle pylint pyqt5-stubs`

PyQt5 stubs may be incomplete when it comes to signals.
