# No Spaghetti Code

## Single Responsibility

- Each function does ONE thing; use an orchestrator function to compose steps
- If you can't name the function clearly, it does too much

## Function Size

- Functions ≤30 lines (excluding docstrings)
- If a function needs comments explaining sections, split it

## No Deep Nesting

- Maximum 3 levels of indentation inside functions
- Flatten with early returns, list comprehensions, and helper functions

## Early Returns (Guard Clauses)

- Validate and exit early to reduce nesting
- Put error checks at the top, happy path at the bottom

## Dependency Injection

- Pass dependencies as parameters; don't instantiate inside functions
- This makes functions testable and decoupled

## Avoid God Objects

- Classes: max 7-10 public methods
- No unrelated concerns in one class
- Avoid generic names (`Manager`, `Handler`, `Processor`) without specificity
