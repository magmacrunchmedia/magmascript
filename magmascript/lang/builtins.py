from __future__ import annotations

from typing import Any, Callable


class HttpProxy:
    """HTTP client for making requests from .mgs scripts."""

    def get(self, url: str, **kwargs: Any) -> dict:
        """Make a GET request and return status, text, json, headers."""
        import httpx
        try:
            response = httpx.get(url, timeout=30, **kwargs)
            result: dict[str, Any] = {
                "status": response.status_code,
                "text": response.text,
                "headers": dict(response.headers),
            }
            try:
                result["json"] = response.json()
            except Exception:
                result["json"] = None
            return result
        except httpx.TimeoutException:
            raise TimeoutError(f"http.get: request timed out after 30 seconds: {url}")
        except httpx.RequestError as e:
            raise ConnectionError(f"http.get: request failed: {e}")

    def post(self, url: str, body: Any = None, **kwargs: Any) -> dict:
        """Make a POST request and return status, text, json, headers."""
        import httpx
        try:
            response = httpx.post(url, json=body, timeout=30, **kwargs)
            result = {
                "status": response.status_code,
                "text": response.text,
                "headers": dict(response.headers),
            }
            try:
                result["json"] = response.json()
            except Exception:
                result["json"] = None
            return result
        except httpx.TimeoutException:
            raise TimeoutError(f"http.post: request timed out after 30 seconds: {url}")
        except httpx.RequestError as e:
            raise ConnectionError(f"http.post: request failed: {e}")


def to_display(value: Any, *, nested: bool = False) -> str:
    """Render a value the way MagmaScript spells it.

    Python's str() leaks its own vocabulary - None, True, False - into a
    language whose literals are none, true and false. Everything that shows a
    value to the user goes through here so the spelling is the same in print,
    echo, f-strings and str().

    Strings print bare at the top level but quoted inside a container, so
    ["a", "b"] stays readable as a list of two strings.
    """
    from magmascript.lang.domain_bridge import ListWrapper

    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"' if nested else value
    if isinstance(value, (list, ListWrapper)):
        return "[" + ", ".join(to_display(v, nested=True) for v in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(
            f"{to_display(k, nested=True)}: {to_display(v, nested=True)}"
            for k, v in value.items()
        )
        return "{" + inner + "}"
    return str(value)


def builtin_print(*args: Any) -> None:
    print(*[to_display(a) for a in args])


def builtin_echo(*args: Any) -> None:
    print(*[to_display(a) for a in args])


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
    from magmascript.lang.interpreter import MgsClass, MgsInstance
    from magmascript.lang.astheno import Fixed, SpecHandle
    if value is None:
        return "none"
    if isinstance(value, Fixed):
        return value.spec.name
    if isinstance(value, SpecHandle):
        return "width"
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
    if isinstance(value, MgsInstance):
        return value.class_def.name
    if isinstance(value, MgsClass):
        return "class"
    if callable(value):
        return "function"
    return "object"


def builtin_str(value: Any) -> str:
    return to_display(value)


def builtin_int(value: Any) -> int:
    from magmascript.lang.astheno import Fixed
    if isinstance(value, Fixed):
        return int(value.value)
    if isinstance(value, str):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    raise TypeError(f"int() expected string or number, got {type(value).__name__}")


def builtin_float(value: Any) -> float:
    from magmascript.lang.astheno import Fixed
    if isinstance(value, Fixed):
        return float(value.value)
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


def builtin_abs(value: Any) -> Any:
    from magmascript.lang.astheno import Fixed, coerce
    if isinstance(value, Fixed):
        return coerce(abs(value.value), value.spec, context="abs()")
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
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"quarry: file not found: {path}")
    except IsADirectoryError:
        raise IsADirectoryError(f"quarry: is a directory: {path}")


def builtin_litho(path: str, content: str) -> None:
    """Write content to file (lithography - writing on stone)."""
    from pathlib import Path
    try:
        Path(path).write_text(content, encoding="utf-8")
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

# The Asthenosphere's widths and conversions. Registered as builtins rather
# than keywords so a script that already uses these names keeps working.
from magmascript.lang.astheno import ASTHENO_BUILTINS  # noqa: E402

BUILTINS.update(ASTHENO_BUILTINS)
