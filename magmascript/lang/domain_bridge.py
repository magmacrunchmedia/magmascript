from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from magmascript.core.registry import get_domain, list_domains, register_domain

# Packages outside this repo publish domains under this entry-point group.
ENTRY_POINT_GROUP = "magmascript.domains"


class DomainProxy:
    """A domain, exposed to scripts under its name.

    The client is built on first use, not at interpreter startup. Every domain
    used to be constructed for every script and every REPL session, which cost
    startup time for domains nobody touched and ruled out any domain whose
    construction does something — opening a window, holding a socket.
    """

    def __init__(self, name: str, client: Any = None, *,
                 factory: Any = None) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_factory", factory)
        object.__setattr__(self, "_client_cache", client)

    @property
    def _client(self) -> Any:
        client = object.__getattribute__(self, "_client_cache")
        if client is None:
            factory = object.__getattribute__(self, "_factory")
            if factory is None:
                name = object.__getattribute__(self, "_name")
                raise AttributeError(f"domain '{name}' has no client")
            client = factory()
            object.__setattr__(self, "_client_cache", client)
        return client

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

    def close(self) -> None:
        # Only a client that was actually built can need closing, and touching
        # self._client here would construct one just to tear it down.
        client = object.__getattribute__(self, "_client_cache")
        if client is not None and hasattr(client, "close"):
            try:
                client.close()
            except Exception:
                pass

    def __del__(self) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<domain:{self._name}>"


class DataclassWrapper:
    def __init__(self, obj: Any) -> None:
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> Any:
        obj = object.__getattribute__(self, "_obj")
        if name.startswith("_"):
            raise AttributeError(name)
        if is_dataclass(obj) and not isinstance(obj, type):
            for f in fields(obj):
                if f.name == name:
                    return wrap_result(getattr(obj, name))
        # Not a field, but dataclasses carry properties and methods too, and a
        # script has no way to tell which is which. InputState.dx and
        # ControllerState.up are properties over the fields; without this a
        # script could read the raw buttons byte but not the buttons.
        try:
            return wrap_result(getattr(obj, name))
        except AttributeError:
            raise AttributeError(
                f"'{type(obj).__name__}' has no attribute '{name}'"
            ) from None

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
    from magmascript.lang.interpreter import MgsInstance, MgsClass
    from magmascript.lang.astheno import Fixed, Pine
    if result is None:
        return None
    if isinstance(result, (int, float, str, bool)):
        return result
    # Asthenosphere values are dataclasses but are language primitives, not
    # host objects to be introspected. They must not be wrapped.
    if isinstance(result, (Fixed, Pine)):
        return result
    if callable(result):
        return result
    if isinstance(result, (MgsInstance, MgsClass)):
        return result
    if isinstance(result, list):
        return ListWrapper(result)
    if is_dataclass(result) and not isinstance(result, type):
        return DataclassWrapper(result)
    return result


def _domain_factory(name: str) -> Any:
    """Build the thunk that constructs one domain's client on first use.

    A constructor that raises now surfaces at the call that needed it, rather
    than the domain silently not existing and the script reporting an undefined
    variable several lines later.
    """

    def build() -> Any:
        from magmascript.core.config import get_config

        return get_domain(name)(get_config())

    return build


def discover_domains() -> None:
    """Register domains published by other installed packages.

    A package declares one in its own metadata::

        [project.entry-points."magmascript.domains"]
        texastoast = "texastoast.mgs:TexastoastDomain"

    which is what lets a domain live in the project it belongs to rather than
    in this repo. Built-ins win on a name clash, and a broken entry point is
    skipped rather than taking the interpreter down with it.
    """
    from importlib.metadata import entry_points

    try:
        found = entry_points(group=ENTRY_POINT_GROUP)
    except Exception:
        # Broken installed metadata is not this interpreter's problem to solve,
        # and must not stop a script that uses only built-in domains.
        return

    builtins = set(list_domains())
    for entry in found:
        if entry.name in builtins:
            continue
        try:
            register_domain(entry.name, entry.load())
        except Exception:
            # A third-party package that fails to import must not stop a script
            # that never mentions it from running.
            continue


def create_domain_proxies() -> dict[str, DomainProxy]:
    discover_domains()
    return {
        name: DomainProxy(name, factory=_domain_factory(name))
        for name in list_domains()
    }
