# Large-Scale Data Handling (12M+ Items)

## Rules

- Use generators/iterators instead of loading everything into memory
- Use `@dataclass(slots=True)` for objects instantiated millions of times
- Target O(n) or better; avoid O(n²) patterns (e.g., use `set` for membership checks)
- Process in configurable batches (default ~1000 records)
- Use parameterized queries; batch inserts 500-1000 per batch; use connection pooling
- Profile before parallelizing

## Data Structure Selection

| Operation | Use | Avoid |
|-----------|-----|-------|
| Membership test | `set` | `list` |
| Key-value lookup | `dict` | list of tuples |
| Ordered unique | `dict` (3.7+) | `OrderedDict` |
| Numeric arrays | `numpy.ndarray` | `list[float]` |
| Queue operations | `collections.deque` | `list` |

## Parallelization

- `multiprocessing.Pool` for CPU-bound work
- `asyncio` for I/O-bound work
- `concurrent.futures` for simple parallel execution
