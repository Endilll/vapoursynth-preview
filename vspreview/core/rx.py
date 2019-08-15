from __future__ import annotations

from typing import Any, Callable, cast, Optional, TypeVar

from rx             import create
from rx.core.typing import Observable, Observer, Scheduler
from rx.disposable.disposable import Disposable

T = TypeVar("T")
U = TypeVar("U")


def repeat_last_when(trigger: Observable[U], predicate: Callable[[U], bool]) -> Callable[[Observable[T]], Observable[T]]:
    def _repeat_last_when(source: Observable[T]) -> Observable[T]:
        source_observer = cast(Observer, None)
        last_value = cast(T, None)

        def repeat_last_value(value: U) -> None:
            if predicate(value):
                source_observer.on_next(last_value)
        trigger.subscribe(repeat_last_value)  # type: ignore

        def subscribe(observer: Observer[T], scheduler: Optional[Scheduler] = None) -> Disposable:
            nonlocal source_observer
            source_observer = observer

            def on_next(value: Any) -> None:
                nonlocal last_value
                last_value = value
                observer.on_next(value)

            return source.subscribe(  # type: ignore
                on_next,
                observer.on_error,
                observer.on_completed,
                scheduler)
        return create(subscribe)
    return _repeat_last_when
