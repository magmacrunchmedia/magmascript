from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from magmascript.lang.util import suggest


class EnvironmentError(Exception):
    def __init__(self, message: str, suggestion: str | None = None) -> None:
        self.suggestion = suggestion
        super().__init__(message)


@dataclass
class Environment:
    parent: Environment | None = None
    variables: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent is not None:
            return self.parent.get(name)
        candidates = self._collect_names()
        hint = suggest(name, candidates) if candidates else None
        raise EnvironmentError(f"Undefined variable '{name}'", hint)

    def set(self, name: str, value: Any) -> None:
        if name in self.variables:
            self.variables[name] = value
            return
        if self.parent is not None and self.parent.has(name):
            self.parent.set(name, value)
            return
        self.variables[name] = value

    def define(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def has(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def child(self) -> Environment:
        return Environment(parent=self)

    def _collect_names(self) -> list[str]:
        names = list(self.variables.keys())
        if self.parent is not None:
            names.extend(self.parent._collect_names())
        return names
