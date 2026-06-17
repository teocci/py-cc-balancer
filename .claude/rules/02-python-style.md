# Python Style & Formatting

## String Literals

- Use single quotes (`'`) for all string literals
- Use double quotes (`"`) only when the string contains single quotes
- Use triple single quotes (`"""`) for docstrings and multi-line strings

```python
# Correct
name = 'example'
message = 'Hello, world!'
sql = "SELECT * FROM users WHERE name = 'John'"

# Incorrect
name = "example"
```

## Imports

- Group imports: stdlib → third-party → local (separated by blank lines)
- Use absolute imports over relative imports
- Never use wildcard imports (`from module import *`)
- Import only what is needed

```python
import os
import sys
from pathlib import Path

import numpy as np

from mypackage.utils import helper
from mypackage.core import processor
```

## Naming Conventions

- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Prefix private attributes with single underscore (`_private`)
- No double underscores unless implementing dunder methods
