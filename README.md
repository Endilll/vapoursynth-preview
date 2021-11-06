Standalone preview for VapourSynth scripts. Meant to be paired with a code editor with integrated terminal like Visual Studio Code.

Feel free to contact me in [Telegram chat](https://t.me/vspreview_chat). Any feedback is appreciated.

# Prerequisites

* Python 3.9
* Vapoursynth R53
* pip modules in `requirements.txt`

You can use the following command to install pip modules:

`pip install -r requirements.txt`

# Installation and usage
There are two ways to install this package using Python's `pip` module. The first is using editable mode
for development purposes, the second is using the git protocol with `pip`.

Editable mode allows any changes made locally to take effect when the module gets reloaded.
```bash
# For development versions, clone the repository and install it in editable mode:
git clone https://github.com/Endilll/vapoursynth-preview.git
cd vapoursynth-preview
python -m pip install -e ./

# Install the latest from git master:
python -m pip install -U git+https://github.com/Endilll/vapoursynth-preview.git
```

You can also download and add this directory (repository root) to your *PYTHONPATH* manually.
Using the above ways to install vspreview, it can be used by running `python -m vspreview script.vpy`.

Alternatively, download this repository anywhere else and use it by running `python run.py script.vpy`.


# Example Installation

* [VSCode](docs/vscode_install.md)

# Note

WIP, so there're some debug stuff among the logic, but not much.

# Development

pip modules:

`mypy pycodestyle pylint pyqt5-stubs`

PyQt5 stubs may be incomplete when it comes to signals.
