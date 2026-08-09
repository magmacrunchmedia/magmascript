from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from magmascript.core.registry import get_domain, list_domains


class DomainProxy:
    def __init__(self, name: str, client: Any) -> None:
        self._name = name
        self._client = client

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        method = getattr(self._client, name, None)
        if method is None:
            raise AttributeError(f"'{self._name}' has no method '{name}'")

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = method(*args, **kwargs)
            return wrap_result(result)

        return wrapper

    def __repr__(self) -> str:
        return f"<domain:{self._name}>"


class DataclassWrapper:
    def __init__(self, obj: Any) -> None:
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> Any:
        obj = object.__getattribute__(self, "_obj")
        if is_dataclass(obj) and not isinstance(obj, type):
            for f in fields(obj):
                if f.name == name:
                    return wrap_result(getattr(obj, name))
        raise AttributeError(f"'{type(obj).__name__}' has no attribute '{name}'")

    def __repr__(self) -> str:
        obj = object.__getattribute__(self, "_obj")
        return repr(obj)

    def __str__(self) -> str:
        obj = object.__getattribute__(self, "_obj")
        return str(obj)


class ListWrapper:
    def __init__(self, items: list[Any]) -> None:
        self._items = [wrap_result(item) for item in items]

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Any:
        return iter(self._items)

    def __repr__(self) -> str:
        return repr(self._items)

    def __str__(self) -> str:
        return str(self._items)


def wrap_result(result: Any) -> Any:
    if result is None:
        return None
    if isinstance(result, (int, float, str, bool)):
        return result
    if isinstance(result, list):
        return ListWrapper(result)
    if is_dataclass(result) and not isinstance(result, type):
        return DataclassWrapper(result)
    return result


def create_domain_proxies() -> dict[str, DomainProxy]:
    proxies = {}
    for name in list_domains():
        try:
            client = get_domain(name)
            proxies[name] = DomainProxy(name, client)
        except Exception:
            pass
    return proxies
