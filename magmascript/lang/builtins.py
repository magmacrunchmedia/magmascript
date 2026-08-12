from __future__ import annotations

from typing import Any, Callable


def builtin_print(*args: Any) -> None:
    print(*[str(a) for a in args])


def builtin_echo(*args: Any) -> None:
    print(*[str(a) for a in args])


def builtin_len(value: Any) -> int:
    from magmascript.lang.domain_bridge import ListWrapper, DataclassWrapper
    if isinstance(value, (str, list, dict, ListWrapper)):
        return len(value)
    if isinstance(value, DataclassWrapper):
        obj = object.__getattribute__(value, "_obj")
        if hasattr(obj, "__len__"):
            return len(obj)
    raise TypeError(f"len() expected string, list, or dict, got {type(value).__name__}")


def builtin_type(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if callable(value):
        return "function"
    return "object"


def builtin_str(value: Any) -> str:
    if value is None:
        return "none"
    return str(value)


def builtin_int(value: Any) -> int:
    if isinstance(value, str):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    raise TypeError(f"int() expected string or number, got {type(value).__name__}")


def builtin_float(value: Any) -> float:
    if isinstance(value, str):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(f"float() expected string or number, got {type(value).__name__}")


def builtin_range(*args: Any) -> list[int]:
    if len(args) == 1:
        return list(range(int(args[0])))
    if len(args) == 2:
        return list(range(int(args[0]), int(args[1])))
    if len(args) == 3:
        return list(range(int(args[0]), int(args[1]), int(args[2])))
    raise TypeError(f"range() takes 1-3 arguments, got {len(args)}")


def builtin_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return list(value.keys())
    raise TypeError(f"keys() expected dict, got {type(value).__name__}")


def builtin_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(value.values())
    raise TypeError(f"values() expected dict, got {type(value).__name__}")


def builtin_abs(value: Any) -> int | float:
    if isinstance(value, (int, float)):
        return abs(value)
    raise TypeError(f"abs() expected number, got {type(value).__name__}")


def builtin_min(*args: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], list):
        return min(args[0])
    return min(args)


def builtin_max(*args: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], list):
        return max(args[0])
    return max(args)


def builtin_sum(*args: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], list):
        return sum(args[0])
    return sum(args)


def builtin_quarry(path: str) -> str:
    """Read file contents (quarry stone from the ground)."""
    from pathlib import Path
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        raise FileNotFoundError(f"quarry: file not found: {path}")
    except IsADirectoryError:
        raise IsADirectoryError(f"quarry: is a directory: {path}")


def builtin_litho(path: str, content: str) -> None:
    """Write content to file (lithography - writing on stone)."""
    from pathlib import Path
    try:
        Path(path).write_text(content)
    except IsADirectoryError:
        raise IsADirectoryError(f"litho: is a directory: {path}")


def builtin_exec(command: str) -> dict:
    """Execute a shell command and return stdout, stderr, and exit code."""
    import subprocess
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"exec: command timed out after 30 seconds: {command}")


BUILTINS: dict[str, Callable] = {
    "print": builtin_print,
    "echo": builtin_echo,
    "len": builtin_len,
    "type": builtin_type,
    "str": builtin_str,
    "int": builtin_int,
    "float": builtin_float,
    "range": builtin_range,
    "keys": builtin_keys,
    "values": builtin_values,
    "abs": builtin_abs,
    "min": builtin_min,
    "max": builtin_max,
    "sum": builtin_sum,
    "quarry": builtin_quarry,
    "litho": builtin_litho,
    "exec": builtin_exec,
}
