# Module Organization

## Rules

- One module per file; no monolithic files
- Target 300-500 lines per file; max ~700 (excluding tests)
- If exceeding limit, split by responsibility

## Module Contents Order

1. Module docstring
2. `__all__` (if public API)
3. Imports (stdlib → third-party → local)
4. Constants
5. Exceptions
6. Classes
7. Functions
8. `if __name__ == '__main__':` entry point

## Package Exports

- Define `__all__` in `__init__.py` to control public API

## Circular Import Prevention

- Use `from __future__ import annotations` and `TYPE_CHECKING` for type-only imports
- Structure dependencies as a DAG (no cycles)
