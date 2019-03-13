# original: https://stackoverflow.com/a/50381071
# pylint: skip-file
from __future__ import annotations

from abc    import ABCMeta as NativeABCMeta
from typing import Any, cast, Optional, TypeVar, Union


T = TypeVar('T')


class DummyAttribute:
    pass


def abstract_attribute(obj: Optional[T] = None) -> T:
    if obj is None:
        obj = DummyAttribute()  # type: ignore
    obj.__is_abstract_attribute__ = True  # type: ignore
    return cast(T, obj)


class ABCMeta(NativeABCMeta):
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        instance = NativeABCMeta.__call__(cls, *args, **kwargs)
        abstract_attributes = []
        for name in dir(instance):
            attr = getattr(instance, name, None)
            if attr is not None:
                if getattr(attr, '__is_abstract_attribute__', False):
                    abstract_attributes.append(name)

        if len(abstract_attributes) > 0:
            raise NotImplementedError(
                "Class {} doesn't initialize abstract attributes with values: {}"
                .format(cls.__name__, ', '.join(abstract_attributes))
            )
        return instance


class ABC(metaclass=ABCMeta):
    pass
