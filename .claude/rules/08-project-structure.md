# Project Structure (Pythonic Approach)

Simple is better than complex. Flat is better than nested. Practicality beats purity.

## Standard Directory Layout

```
project/
├── pyproject.toml
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── config.py          # Settings via environment/files
│       ├── constants.py       # Project-wide constants
│       ├── exceptions.py      # Custom exceptions
│       ├── enums/             # VerbosityLevel, Status, etc.
│       ├── models/            # Data classes (domain objects)
│       ├── stores/            # Data access (all backends)
│       ├── managers/          # Business logic / orchestration
│       └── utils/             # Helpers
└── tests/
```

## Data Access Pattern Decision Guide

- **Single database** → module with functions (default choice, simplest)
- **Shared state across methods** → dataclass store with injected db
- **Swappable backends** (e.g., PostgreSQL ↔ MySQL) → Protocol-based
- **Different paradigms** (SQL + Vector + Graph) → separate client modules, coordinate in managers

## What to Avoid

| Anti-Pattern | Why |
|--------------|-----|
| `BaseClient(ABC)` for all stores | They don't share behavior |
| `BaseRepository` inheritance | Boilerplate, no benefit in Python |
| Deep hierarchies | Flat is better than nested |
| Interfaces for single implementation | YAGNI |
| Java-style factories | Python has simpler patterns |

**Rule of thumb:** If you're writing `BaseAnything`, stop and ask if you really need it.
