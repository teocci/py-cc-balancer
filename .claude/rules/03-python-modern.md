# Python 3.11+ Modern Syntax

## Type Hints

- Use built-in generic types (lowercase): `list[str]`, `dict[str, int]`, `tuple[int, str]`
- Do NOT import from `typing`: no `Dict`, `List`, `Tuple`, `Set`, `Type`, `Optional`, `Union`

## Union Syntax

- Use `X | Y` instead of `Union[X, Y]`
- Use `X | None` instead of `Optional[X]`

## Features to Leverage

- `match`/`case` for complex conditionals
- Exception groups and `except*` for concurrent error handling
- `tomllib` for TOML parsing (stdlib)
- `Self` type from `typing` for methods returning instance type
- f-strings with `=` for debugging: `f'{value=}'`

## Avoid

- All legacy `typing` generics
- Legacy string formatting (`%` or `.format()`) — use f-strings
