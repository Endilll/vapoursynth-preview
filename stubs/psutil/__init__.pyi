from typing import List, Optional, Union, overload

# pylint: skip-file


class Process:
    @overload
    def cpu_affinity(self, cpus: None = ...) -> List[int]: ...
    @overload
    def cpu_affinity(self, cpus: List[int] = ...) -> None: ...
    @overload
    def cpu_affinity(self, cpus: Optional[List[int]] = ...) -> Union[List[int], None]: ...


def cpu_count(logical: bool = ...) -> int: ...
