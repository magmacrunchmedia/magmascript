"""MagmaScript scaffolding.

Generate project structures, modules, and boilerplate.

Usage::

    from magmascript.scaffold import scaffold_module
    scaffold_module("my_module")
"""

from __future__ import annotations

from pathlib import Path


MODULE_TEMPLATE = '''# {name} - MagmaScript module
#
# Description: TODO
# Usage: intent "{name}" from "./{name}"

fn hello() {{
    print("Hello from {name}!")
}}

fn greet(name) {{
    print(f"Hello, {{name}}!")
}}
'''


MODULE_TEST_TEMPLATE = '''# Tests for {name} module
#
# Run with: magmascript tests/test_{name}.mgs

intent {{ hello, greet }} from "./{name}"

// Test hello()
hello()

// Test greet()
greet("World")
print("All tests passed!")
'''


def scaffold_module(name: str, path: str = ".") -> Path:
    """Generate a new MagmaScript module with boilerplate.

    Creates:
        - {name}/{name}.mgs (main module)
        - {name}/tests/test_{name}.mgs (tests)

    Returns the path to the created module directory.
    """
    module_dir = Path(path) / name
    module_dir.mkdir(parents=True, exist_ok=True)

    # Create main module file
    module_file = module_dir / f"{name}.mgs"
    module_file.write_text(MODULE_TEMPLATE.format(name=name))

    # Create tests directory
    tests_dir = module_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Create test file
    test_file = tests_dir / f"test_{name}.mgs"
    test_file.write_text(MODULE_TEST_TEMPLATE.format(name=name))

    return module_dir
