from typing import Iterator

# pylint: skip-file

class SSAEvent:
    def __init__(self) -> None:
        self.start: int

class SSAFile:
    @classmethod
    def load(self, path: str) -> 'SSAFile': ...

    def __iter__(self) -> Iterator[SSAEvent]: ...

load = SSAFile.load
