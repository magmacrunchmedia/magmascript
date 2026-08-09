from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class EnvironmentError(Exception):
    pass


@dataclass
class Environment:
    parent: Environment | None = None
    variables: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise EnvironmentError(f"Undefined variable: {name}")

    def set(self, name: str, value: Any) -> None:
        if name in self.variables:
            self.variables[name] = value
            return
        if self.parent is not None:
            try:
                self.parent.set(name, value)
                return
            except EnvironmentError:
                pass
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
