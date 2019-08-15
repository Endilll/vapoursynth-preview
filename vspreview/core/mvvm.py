from __future__ import annotations

# pylint: disable=pointless-statement,function-redefined

from enum import auto, Flag
from typing import (  # type: ignore
    Any, Callable, Dict, Generic, List, Optional, overload, TypeVar, Type,
    Union, _GenericAlias,
)

from PySide2.QtCore import QObject, Signal  # type: ignore
from PySide2.QtWidgets import QWidget
from rx.core import Observer, Observable
from rx.core.typing import Scheduler
from rx.disposable import Disposable

from .metatypes import QObservable

T = TypeVar('T')
U = TypeVar('U')


class Property(QObservable, Generic[T]):  # pylint: disable=unsubscriptable-object
    _specializations: Dict[Type, Type[Property]] = {}  # pylint: disable=undefined-variable

    def __class_getitem__(cls, ty: Type) -> Type[Property]:  # pylint: disable=no-self-argument
        if ty.__class__ is _GenericAlias:
            ty = ty.__args__[0]

        if ty in cls._specializations:
            return cls._specializations[ty]

        dct = {
            'ty': ty,
            '_value_changed': Signal(ty),
        }

        spec = type(cls.__name__, (cls,), dct)
        cls._specializations[ty] = spec
        return spec

    @property
    def name(self) -> str:
        return self._name

    @property
    def owner(self) -> Optional[Type[U]]:
        return self._owner

    def __init__(self, init_value: T) -> None:
        def subscribe(observer: Observer, scheduler: Optional[Scheduler] = None) -> Disposable:
            def action(value: T) -> None:
                observer.on_next(value)
            assert self._value_changed.connect(action)

            return Disposable()

        assert hasattr(self, 'ty'), '{} requires type of underlying data to be specified'.format(type(self).__name__)

        super().__init__(subscribe)  # type: ignore

        self._value = init_value
        self._name = ""
        self._owner: Optional[Type] = None

    def __set_name__(self, owner: Type[U], name: str) -> None:
        self._name = name
        self._owner = owner

    @overload
    def __get__(self, instance: None, owner: Type[U]) -> Property: ...
    @overload
    def __get__(self, instance: U, owner: Type[U]) -> T: ...
    def __get__(self, instance, owner):  # type: ignore
        if instance is None:
            return self
        return self._value

    def __set__(self, instance: ViewModel, value: Union[T, Observable]) -> None:
        def update(value: T) -> None:
            if value == self._value:
                return
            self._value = value
            instance.property_changed.emit(self)
            self._value_changed.emit(self._value)

        if instance is None:
            raise AttributeError

        if isinstance(value, Observable):
            value.subscribe(on_next=update)
        else:
            update(value)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return '{} = {}[{}]({})'.format(self.name, type(self).__name__, self.ty.__name__, self._value)


class ViewModel(QObject):
    property_changed = Signal(Property)


class View(QWidget):
    class BindKind(Flag):
        SOURCE_TO_VIEW = auto()
        VIEW_TO_SOURCE = auto()
        BIDIRECTIONAL  = SOURCE_TO_VIEW | VIEW_TO_SOURCE

        @classmethod
        def is_from_source(cls, value: Any) -> bool:
            return value in (cls.SOURCE_TO_VIEW, cls.BIDIRECTIONAL)

        @classmethod
        def is_from_view(cls, value: Any) -> bool:
            return value in (cls.VIEW_TO_SOURCE, cls.BIDIRECTIONAL)

    @property
    def data_context(self) -> ViewModel:
        return self._data_context

    def __init__(self, data_context: ViewModel, init_super: bool = True):
        if init_super:
            super().__init__()
        self._data_context = data_context
        self._properties = type(self._data_context)
        self._listeners: Dict[Property, List[Callable]] = {}

        ret = self.data_context.property_changed.connect(self.on_property_changed)
        assert ret

    def add_property_listener(self, prop: Property, listener: Callable) -> None:
        if prop not in self._listeners:
            self._listeners[prop] = []
        self._listeners[prop].append(listener)

    def on_property_changed(self, prop: Property) -> None:
        for listener in self._listeners[prop]:
            listener()
